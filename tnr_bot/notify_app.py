"""
HTTP webhook for Airtable Automations: POST /notify/airtable

Run locally: uvicorn tnr_bot.notify_app:app --host 127.0.0.1 --port 8080
Expose with ngrok: ngrok http 8080
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from tnr_bot.integrations.airtable import (
    fetch_all_operator_records,
    fetch_matching_records_missing_telegram_chat_id,
    fetch_record_by_id,
    operators_match_field,
    operators_telegram_field,
    resolve_telegram_chat_id_for_notify,
    sterilization_language_field,
)
from tnr_bot.integrations.airtable_write import patch_telegram_chat_id_on_records
from tnr_bot.integrations.telegram_api import send_message
from tnr_bot.locale import default_notify_locale, locale_from_airtable_value, normalize_locale
from tnr_bot.utils.formatting import (
    OperatorDirectory,
    build_notify_new_request_message,
    build_notify_operator_assigned_message,
    build_notify_status_changed_message,
    build_operator_directory,
)
from tnr_bot.utils.telegram_identity import normalize_handle

logger = logging.getLogger(__name__)

app = FastAPI(title="TNR Airtable notify webhook", version="0.1.0")

# Short-window dedup for automation double-fires (seconds). Keyed by record_id + event
# so operator and status updates in quick succession are not suppressed.
_DEDUP_SEC = 45.0
_recent_notify_times: dict[str, float] = {}

NotifyEvent = Literal["new_request", "operator_assigned", "status_changed"]


def _normalize_notify_event(raw: str | None) -> NotifyEvent:
    if raw is None or not str(raw).strip():
        return "new_request"
    s = str(raw).strip().lower().replace("-", "_")
    if s in ("new_request", "operator_assigned", "status_changed"):
        return s
    logger.warning("Unknown notify event %r; using new_request", raw)
    return "new_request"


def _dedup_key(record_id: str, event: NotifyEvent) -> str:
    return f"{record_id}:{event}"


class NotifyBody(BaseModel):
    """JSON body from Airtable automation or curl."""

    model_config = ConfigDict(extra="ignore")

    record_id: str | None = Field(None, description="Airtable record id rec…")
    recordId: str | None = Field(None, description="camelCase alias")
    secret: str | None = Field(None, description="Optional body secret if headers unavailable")
    event: str | None = Field(
        None,
        description="new_request | operator_assigned | status_changed (aliases: notify_type)",
    )
    notify_type: str | None = Field(None, description="Alias for event")
    locale: str | None = Field(
        None,
        description="Message language: en | ru | ka (overrides Airtable language + NOTIFY_DEFAULT_LOCALE)",
    )


def _notify_locale(payload: NotifyBody, record: dict[str, Any]) -> str:
    if payload.locale is not None and str(payload.locale).strip():
        return normalize_locale(str(payload.locale).strip())
    fields = record.get("fields") or {}
    raw = fields.get(sterilization_language_field())
    at = locale_from_airtable_value(raw)
    if at is not None:
        return at
    return default_notify_locale()


def _get_record_id(payload: NotifyBody) -> str:
    rid = payload.record_id or payload.recordId
    if not rid or not str(rid).strip():
        raise HTTPException(status_code=400, detail="record_id or recordId is required")
    return str(rid).strip()


def _get_notify_event(payload: NotifyBody) -> NotifyEvent:
    return _normalize_notify_event(payload.event or payload.notify_type)


def _build_message_for_event(
    record: dict[str, Any],
    event: NotifyEvent,
    operator_directory: OperatorDirectory | None,
    *,
    locale: str,
) -> str:
    if event == "operator_assigned":
        return build_notify_operator_assigned_message(
            record, operator_directory=operator_directory, locale=locale
        )
    if event == "status_changed":
        return build_notify_status_changed_message(
            record, operator_directory=operator_directory, locale=locale
        )
    return build_notify_new_request_message(
        record, operator_directory=operator_directory, locale=locale
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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
        operator_directory = build_operator_directory(
            op_recs,
            match_field=operators_match_field(),
            telegram_field=operators_telegram_field(),
        )
    except Exception:
        logger.warning("Could not load operators table for notify operator labels", exc_info=True)

    loc = _notify_locale(payload, record)
    text = _build_message_for_event(record, event, operator_directory, locale=loc)

    await send_message(chat_id, text)

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
