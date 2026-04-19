"""Optional writes to Airtable (requires data.records:write on the PAT)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from tnr_bot.config import get_airtable_credentials
from tnr_bot.integrations.airtable import AIRTABLE_API, STERILIZATION_TABLE

logger = logging.getLogger(__name__)


def sync_chat_id_enabled() -> bool:
    return os.getenv("SYNC_TELEGRAM_CHAT_ID", "").strip().lower() in ("1", "true", "yes")


async def patch_telegram_chat_id_on_records(record_ids: list[str], chat_id: int) -> None:
    """
    Set telegram_chat_id on the given records (batches of 10 per Airtable API).
    """
    if not record_ids:
        return

    pat, base_id = get_airtable_credentials()
    if not pat or not base_id:
        raise RuntimeError("Airtable credentials are not configured")

    url = f"{AIRTABLE_API}/{base_id}/{STERILIZATION_TABLE}"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(record_ids), 10):
            chunk = record_ids[i : i + 10]
            body: dict[str, Any] = {
                "records": [
                    {"id": rid, "fields": {"telegram_chat_id": chat_id}} for rid in chunk
                ]
            }
            r = await client.patch(url, headers=headers, json=body)
            if r.status_code == 422:
                logger.warning(
                    "Airtable PATCH failed (add field telegram_chat_id or check PAT scope): %s",
                    r.text,
                )
                return
            r.raise_for_status()
