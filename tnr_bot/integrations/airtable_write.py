"""Optional writes to Airtable (requires data.records:write on the PAT)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from tnr_bot.config import get_airtable_credentials
from tnr_bot.integrations.airtable import sterilization_table_url

logger = logging.getLogger(__name__)


def sync_chat_id_enabled() -> bool:
    return os.getenv("SYNC_TELEGRAM_CHAT_ID", "").strip().lower() in ("1", "true", "yes")


def _patch_telegram_chat_id_value(chat_id: int) -> int | str:
    """
    Airtable field type must match: Single line text expects a string; Number expects a number.
    Default is string (text columns are common). Set AIRTABLE_TELEGRAM_CHAT_ID_AS_STRING=false
    if your column is a Number field and rejects string values.
    """
    v = os.getenv("AIRTABLE_TELEGRAM_CHAT_ID_AS_STRING", "true").strip().lower()
    if v in ("0", "false", "no"):
        return chat_id
    return str(chat_id)


async def patch_telegram_chat_id_on_records(record_ids: list[str], chat_id: int) -> bool:
    """
    Set telegram_chat_id on the given records (batches of 10 per Airtable API).

    Returns True if all batches succeeded. Returns False (no exception) when Airtable rejects the
    request in a way that is usually configuration: 422 field/schema, 401/403 auth or missing
    ``data.records:write`` on the PAT for this base.
    """
    if not record_ids:
        return True

    pat, base_id = get_airtable_credentials()
    if not pat or not base_id:
        raise RuntimeError("Airtable credentials are not configured")

    url = sterilization_table_url(base_id)
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
    }

    field_value = _patch_telegram_chat_id_value(chat_id)

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(record_ids), 10):
            chunk = record_ids[i : i + 10]
            body: dict[str, Any] = {
                "records": [
                    {"id": rid, "fields": {"telegram_chat_id": field_value}} for rid in chunk
                ]
            }
            r = await client.patch(url, headers=headers, json=body)
            if r.status_code == 422:
                logger.warning(
                    "Airtable PATCH failed (field telegram_chat_id or value type). "
                    "Use a Single line text or Number column; if INVALID_VALUE_FOR_COLUMN, set "
                    "AIRTABLE_TELEGRAM_CHAT_ID_AS_STRING=true (text) or false (number). Response: %s",
                    r.text,
                )
                return False
            if r.status_code in (401, 403):
                logger.warning(
                    "Airtable PATCH %s: token cannot update records. Create or edit your PAT at "
                    "airtable.com/create/tokens and add scope **data.records:write** for this base. "
                    "Response: %s",
                    r.status_code,
                    (r.text or "")[:800],
                )
                return False
            r.raise_for_status()
    return True
