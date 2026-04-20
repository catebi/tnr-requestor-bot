"""Optional writes to Airtable (requires data.records:write on the PAT)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from tnr_bot.config import get_airtable_credentials
from tnr_bot.integrations.airtable import sterilization_language_field, sterilization_table_url
from tnr_bot.locale import normalize_locale

logger = logging.getLogger(__name__)


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

    # Stored as Single line text in Airtable; API expects a string.
    field_value = str(chat_id)

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
                    "Airtable PATCH failed: add a Single line text field telegram_chat_id (value sent "
                    "as string) or check PAT scope. Response: %s",
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


async def patch_language_on_records(record_ids: list[str], locale_code: str) -> bool:
    """
    Set ``language`` on the given records (batches of 10).

    Values sent are ``en``, ``ru``, or ``ka`` (align Airtable single-select options to these codes).
    """
    if not record_ids:
        return True

    code = normalize_locale(locale_code)
    field_name = sterilization_language_field()
    pat, base_id = get_airtable_credentials()
    if not pat or not base_id:
        raise RuntimeError("Airtable credentials are not configured")

    url = sterilization_table_url(base_id)
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(record_ids), 10):
            chunk = record_ids[i : i + 10]
            body: dict[str, Any] = {
                "records": [
                    {"id": rid, "fields": {field_name: code}} for rid in chunk
                ]
            }
            r = await client.patch(url, headers=headers, json=body)
            if r.status_code == 422:
                logger.warning(
                    "Airtable PATCH language failed: add field %r (single line text or single select "
                    "with options en / ru / ka) or check PAT scope. Response: %s",
                    field_name,
                    r.text,
                )
                return False
            if r.status_code in (401, 403):
                logger.warning(
                    "Airtable PATCH %s: token cannot update records. Response: %s",
                    r.status_code,
                    (r.text or "")[:800],
                )
                return False
            r.raise_for_status()
    return True
