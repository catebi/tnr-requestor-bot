"""
HTTP webhook for Airtable Automations: POST /notify/airtable

Run locally: uvicorn tnr_bot.notify_app:app --host 127.0.0.1 --port 8080
Expose with ngrok: ngrok http 8080
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal, Tuple, Dict

from apscheduler.job import Job
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from tnr_bot.data.recent_history import RecordHistory
from tnr_bot.data.record import Record
from tnr_bot.integrations.airtable import (
    sterilization_language_field,
)
from tnr_bot.locale import default_notify_locale, locale_from_airtable_value, normalize_locale
from tnr_bot.utils.formatting import (
    OperatorDirectory,
    build_notify_new_request_message,
    build_notify_operator_assigned_message,
    build_notify_status_changed_message,
)

logger = logging.getLogger(__name__)

# Short-window dedup for automation double-fires (seconds). Keyed by record_id + event
# so operator and status updates in quick succession are not suppressed.
_DEDUP_SEC = 45.0
recent_history: Dict[str, RecordHistory] = {}

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

