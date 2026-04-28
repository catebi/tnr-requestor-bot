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
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from catebi_telegram_logger.data.logger import LoggerCreateData
from catebi_telegram_logger.logger.setup import setup_logging
from fastapi import FastAPI, Header, HTTPException
from starlette.requests import Request
from telegram import Update
from telegram.ext import Application

from tnr_bot.config import get_airtable_credentials
from tnr_bot.data.recent_history import RecordHistory
from tnr_bot.data.record import Record
from tnr_bot.handlers.register import register_handlers
from tnr_bot.integrations.airtable import fetch_record_by_id, resolve_telegram_chat_id_for_notify, \
    fetch_all_operator_records, fetch_matching_records_missing_telegram_chat_id
from tnr_bot.integrations.airtable_write import patch_telegram_chat_id_on_records
from tnr_bot.integrations.notify import _get_record_id, _get_notify_event, recent_history, _DEDUP_SEC, \
    _notify_locale, _build_message_for_event, NotifyBody
from tnr_bot.runtime.env_profile import env_start, env_shutdown
from tnr_bot.utils.formatting import build_operator_directory
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
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app

    env_profile = os.getenv("BOT_TRANSPORT", "polling")
    logs_chat_var = os.getenv("LOGS_CHAT_ID")
    if not logs_chat_var:
        logger.error("LOGS_CHAT_ID is not set")
    else:
        try:
            logs_chat_id = int(logs_chat_var)
            logger_create_data = LoggerCreateData(
                app=telegram_app,
                loop=asyncio.get_running_loop(),
                logs_chat_id=logs_chat_id,
                app_name=os.getenv('APP_NAME', 'TNR Airtable Notify App'),
                ping_developers=os.getenv('DEVELOPERS'),
                min_level=logging.WARNING,
            )
            setup_logging(logger_create_data)
        except ValueError:
            logger.error(f"LOGS_CHAT_ID must be Integer, got {logs_chat_var}")

    scheduler.start()
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


def is_duplicate(history: Optional[RecordHistory], record: Record) -> bool:
    if not history or not history.last_sent_message_data:
        return False
    return history.last_sent_message_data.fingerprint == record.fingerprint


def skip(reason: str, record_id: str, event: str):
    return {
        "status": f"skipped_{reason}",
        "record_id": record_id,
        "event": event,
    }


async def safe_resolve_chat_id(record_raw, normalized, record_id,
                               event):  # everything Airtable related should be refactored,
    # but major changes will be done in the separate task
    try:
        return await resolve_telegram_chat_id_for_notify(record_raw, normalized)
    except Exception:
        logger.exception("chat_id resolve failed", extra={
            "record_id": record_id,
            "event": event,
        })
        return None


async def load_operator_directory_safe():
    try:
        op_recs = await fetch_all_operator_records()
        return build_operator_directory(op_recs)
    except Exception:
        logger.warning("operator directory load failed", exc_info=True)
        return None


async def safe_backfill_chat_id(normalized, chat_id, record_id):
    try:
        rows = await fetch_matching_records_missing_telegram_chat_id(normalized)
        ids = [r["id"] for r in rows if r.get("id")] or [record_id]

        if await patch_telegram_chat_id_on_records(ids, chat_id):
            return len(ids)
    except Exception:
        logger.exception("backfill failed")

    return 0


def update_history_success(key: str, record: Record):
    history = recent_history.get(key)

    if not history:
        history = RecordHistory(scheduled_time=None,
                                scheduled_job=None,
                                last_sent_message_data=None)
        recent_history[key] = history

    history.last_sent_message_data = record
    history.fail_count = 0


def cleanup_history_if_needed(key: str):
    if len(recent_history) > 5000:
        recent_history.clear()
        return

    recent_history.pop(key, None)


async def send_notification(
        payload: NotifyBody,
        record_id: str
):
    record_raw = await fetch_record_by_id(record_id)
    event = _get_notify_event(payload)

    if not record_raw:
        return skip("not_found", record_id, event)

    fields = record_raw.get("fields") or {}

    record = Record(
        record_id=record_id,
        created_date=fields.get("created_date", ''),
        status=fields.get("status", ''),
        operator=fields.get("operator", ''),
    )

    telegram_raw = fields.get("telegram")
    if not telegram_raw or not str(telegram_raw).strip():
        return skip("no_telegram", record_id, event)

    normalized = normalize_handle(str(telegram_raw).strip())

    chat_id = await safe_resolve_chat_id(record_raw, normalized, record_id, event)
    if chat_id is None:
        return skip("no_chat_id", record_id, event)

    operator_directory = await load_operator_directory_safe()

    loc = _notify_locale(payload, record_raw)
    text = _build_message_for_event(record_raw, event, operator_directory, locale=loc)

    await telegram_app.bot.send_message(chat_id, text)

    update_history_success(record_id, record)

    backfill_count = await safe_backfill_chat_id(normalized, chat_id, record_id)

    cleanup_history_if_needed(record_id)

    return {
        "status": "sent",
        "record_id": record_id,
        "event": event,
        "chat_id": chat_id,
        "telegram_chat_id_rows_patched": backfill_count,
    }


async def schedule_notification(payload: NotifyBody):
    record_id = _get_record_id(payload)
    event = _get_notify_event(payload)

    try:
        return await send_notification(
            payload=payload,
            record_id=record_id
        )

    except Exception:
        logger.exception("send_notification failed", extra={
            "record_id": record_id,
            "event": event,
        })

        history = recent_history.get(record_id)
        if history:
            history.fail_count = getattr(history, "fail_count", 0) + 1

            if history.fail_count >= 3:
                logger.error("Max retries reached, dropping job", extra={"record_id": record_id})
                if history.scheduled_job:
                    history.scheduled_job.remove()
                recent_history.pop(record_id, None)

        return {"status": "error", "record_id": record_id, "event": event}


@app.post("/notify/airtable")
async def notify_airtable(
        payload: NotifyBody,
        x_notify_secret: str | None = Header(None, alias="X-Notify-Secret"),
):
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

    now = datetime.now()
    record_history: Optional[RecordHistory] = recent_history.get(record_id)
    new_scheduled_time = now + timedelta(seconds=_DEDUP_SEC)
    new_job = scheduler.add_job(schedule_notification,
                                trigger='date',
                                run_date=new_scheduled_time,
                                args=[payload],
                                id=record_id,
                                next_run_time=new_scheduled_time,
                                replace_existing=True)

    updated_record_history = RecordHistory(scheduled_time=new_scheduled_time,
                                           scheduled_job=new_job,
                                           last_sent_message_data=record_history.last_sent_message_data
                                           if record_history else None
                                           )

    recent_history[record_id] = updated_record_history
