"""
HTTP webhook for Airtable Automations: POST /notify/airtable

Run locally: uvicorn tnr_bot.notify_app:app --host 127.0.0.1 --port 8080
Expose with ngrok: ngrok http 8080
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from tnr_bot.integrations.airtable import (
    fetch_record_by_id,
    resolve_telegram_chat_id_for_notify,
)
from tnr_bot.integrations.airtable_write import patch_telegram_chat_id_on_records, sync_chat_id_enabled
from tnr_bot.integrations.telegram_api import send_message
from tnr_bot.utils.formatting import build_notify_new_request_message
from tnr_bot.utils.telegram_identity import normalize_handle

logger = logging.getLogger(__name__)

app = FastAPI(title="TNR Airtable notify webhook", version="0.1.0")

# Short-window dedup for automation double-fires (seconds)
_DEDUP_SEC = 45.0
_recent_notify_times: dict[str, float] = {}


class NotifyBody(BaseModel):
    """JSON body from Airtable automation or curl."""

    model_config = ConfigDict(extra="ignore")

    record_id: str | None = Field(None, description="Airtable record id rec…")
    recordId: str | None = Field(None, description="camelCase alias")
    secret: str | None = Field(None, description="Optional body secret if headers unavailable")


def _get_record_id(payload: NotifyBody) -> str:
    rid = payload.record_id or payload.recordId
    if not rid or not str(rid).strip():
        raise HTTPException(status_code=400, detail="record_id or recordId is required")
    return str(rid).strip()


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
    and send a short summary message.
    """
    expected = os.getenv("NOTIFY_WEBHOOK_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="NOTIFY_WEBHOOK_SECRET is not configured")

    provided = (x_notify_secret or "").strip() or (payload.secret or "").strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing secret")

    record_id = _get_record_id(payload)

    now = time.monotonic()
    last = _recent_notify_times.get(record_id)
    if last is not None and (now - last) < _DEDUP_SEC:
        logger.info("Duplicate notify ignored for record_id=%s (within %ss)", record_id, _DEDUP_SEC)
        return {"status": "skipped_duplicate", "record_id": record_id}

    record = await fetch_record_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Record not found: {record_id}")

    fields = record.get("fields") or {}
    telegram_raw = fields.get("telegram")
    if not telegram_raw or not str(telegram_raw).strip():
        logger.info("Record %s has no telegram field; skip send", record_id)
        return {"status": "skipped_no_telegram", "record_id": record_id}

    normalized = normalize_handle(str(telegram_raw).strip())
    chat_id = await resolve_telegram_chat_id_for_notify(record, normalized)
    if chat_id is None:
        logger.info(
            "No telegram_chat_id for handle=%s (user may not have /start the bot yet)",
            normalized,
        )
        return {"status": "skipped_no_chat_id", "record_id": record_id}

    text = build_notify_new_request_message(record)

    await send_message(chat_id, text)

    if sync_chat_id_enabled():
        try:
            await patch_telegram_chat_id_on_records([record_id], chat_id)
        except Exception:
            logger.exception("Optional PATCH telegram_chat_id on notify send failed")

    _recent_notify_times[record_id] = now
    if len(_recent_notify_times) > 5000:
        _recent_notify_times.clear()

    return {"status": "sent", "record_id": record_id, "chat_id": chat_id}
