"""
FastAPI Server for running Telegram Application
and managing HTTP webhooks for Airtable Automations: POST /notify/airtable

Run locally: uvicorn app:app --host 127.0.0.1 --port 8080
Expose with ngrok: ngrok http 8080
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from starlette.requests import Request
from telegram import Update
from telegram.ext import Application

from tnr_bot.config import get_airtable_credentials
from tnr_bot.handlers.register import register_handlers
from tnr_bot.integrations.airtable import fetch_record_by_id, resolve_telegram_chat_id_for_notify, \
    fetch_all_operator_records, fetch_matching_records_missing_telegram_chat_id
from tnr_bot.integrations.airtable_write import patch_telegram_chat_id_on_records
from tnr_bot.integrations.notify import _get_record_id, _get_notify_event, _dedup_key, _recent_notify_times, _DEDUP_SEC, \
    _notify_locale, _build_message_for_event, NotifyBody
from tnr_bot.runtime.env_profile import env_start, env_shutdown
from tnr_bot.utils.formatting import OperatorDirectory, build_operator_directory
from tnr_bot.utils.logger import setup_logging
from tnr_bot.utils.telegram_identity import normalize_handle

logger = logging.getLogger(__name__)


def create_application() -> Application:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")

    pat, base_id = get_airtable_credentials()
    if not pat or not base_id:
        raise SystemExit(
            "Airtable credentials missing: set AIRTABLE_PAT / AIRTABLE_BASE_ID "
            "(or AIRTABLE_*_DEV when ENVIRONMENT=dev)"
        )

    app = Application.builder().token(token).build()
    register_handlers(app)
    return app


telegram_app = create_application()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app

    env_profile = os.getenv("BOT_TRANSPORT", "polling")
    developers = os.getenv("DEVELOPERS")
    logs_chat_id = os.getenv('LOGS_CHAT_ID')
    app_name = os.getenv('APP_NAME')

    loop = asyncio.get_running_loop()

    setup_logging(
        app=telegram_app,
        chat_id=logs_chat_id,
        app_name=app_name,
        ping_developers=developers,
        loop=loop
    )
    await env_start(telegram_app, env_profile)

    yield

    await env_shutdown(telegram_app, env_profile)


app = FastAPI(title="TNR Airtable Notify App", version="0.1.0", lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request):
    global telegram_app
    data = await request.json()

    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)

    return {"ok": True}

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/log_error")
async def log_error(request: Request) -> dict[str, str]:
    global telegram_app
    data = await request.json()
    log_message = f"Airtable automation {data.get('automation_name')} raised error {data.get('error_message')}"

    logger.error(log_message, exc_info=True)
    return data

@app.post("/notify/airtable")
async def notify_airtable(
    payload: NotifyBody,
    x_notify_secret: str | None = Header(None, alias="X-Notify-Secret"),
) -> dict[str, Any]:
    """
    Verify shared secret, load the sterilization_request row, resolve Telegram chat_id,
    and send a message. Optional ``event`` selects the template (default: new_request).
    """
    expected = os.getenv("NOTIFY_WEBHOOK_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="NOTIFY_WEBHOOK_SECRET is not configured")

    provided = (x_notify_secret or "").strip() or (payload.secret or "").strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing secret")

    record_id = _get_record_id(payload)
    event = _get_notify_event(payload)

    now = time.monotonic()
    dk = _dedup_key(record_id, event)
    last = _recent_notify_times.get(dk)
    if last is not None and (now - last) < _DEDUP_SEC:
        logger.info(
            "Duplicate notify ignored for record_id=%s event=%s (within %ss)",
            record_id,
            event,
            _DEDUP_SEC,
        )
        return {"status": "skipped_duplicate", "record_id": record_id, "event": event}

    record = await fetch_record_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Record not found: {record_id}")

    fields = record.get("fields") or {}
    telegram_raw = fields.get("telegram")
    if not telegram_raw or not str(telegram_raw).strip():
        logger.info("Record %s has no telegram field; skip send", record_id)
        return {"status": "skipped_no_telegram", "record_id": record_id, "event": event}

    normalized = normalize_handle(str(telegram_raw).strip())
    chat_id = await resolve_telegram_chat_id_for_notify(record, normalized)
    if chat_id is None:
        logger.info(
            "No telegram_chat_id for handle=%s (user may not have /start the bot yet)",
            normalized,
        )
        return {"status": "skipped_no_chat_id", "record_id": record_id, "event": event}

    operator_directory: OperatorDirectory | None = None
    try:
        op_recs = await fetch_all_operator_records()
        operator_directory = build_operator_directory(op_recs)
    except Exception:
        logger.warning("Could not load operators table for notify operator labels", exc_info=True)

    loc = _notify_locale(payload, record)
    text = _build_message_for_event(record, event, operator_directory, locale=loc)

    await telegram_app.bot.send_message(chat_id, text)

    backfill_count = 0
    try:
        need_chat_id = await fetch_matching_records_missing_telegram_chat_id(normalized)
        ids_to_fix = [r["id"] for r in need_chat_id if r.get("id")]
        if not ids_to_fix:
            ids_to_fix = [record_id]
        ok = await patch_telegram_chat_id_on_records(ids_to_fix, chat_id)
        if ok:
            backfill_count = len(ids_to_fix)
            if backfill_count > 1:
                logger.info(
                    "Set telegram_chat_id on %s row(s) for handle=%s (same user, field was blank)",
                    backfill_count,
                    normalized,
                )
    except Exception:
        logger.exception("PATCH telegram_chat_id after notify (backfill same-handle rows) failed")

    _recent_notify_times[dk] = now
    if len(_recent_notify_times) > 5000:
        _recent_notify_times.clear()

    return {
        "status": "sent",
        "record_id": record_id,
        "event": event,
        "chat_id": chat_id,
        "telegram_chat_id_rows_patched": backfill_count,
    }
