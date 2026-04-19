"""Sterilization request records in Airtable."""

from __future__ import annotations

from typing import Any

import httpx

from tnr_bot.config import get_airtable_credentials

AIRTABLE_API = "https://api.airtable.com/v0"
STERILIZATION_TABLE = "sterilization_request"


def escape_airtable_formula_string(s: str) -> str:
    """Escape single quotes for Airtable formula string literals."""
    return s.replace("'", "''")


def filter_by_telegram_formula(normalized_username: str) -> str:
    """
    Records where `telegram` equals the user's handle, ignoring case and a single leading @.
    """
    esc = escape_airtable_formula_string(normalized_username)
    return (
        "AND("
        "{telegram} != '', "
        "LOWER(TRIM(SUBSTITUTE({telegram}, '@', ''))) = "
        f"'{esc}'"
        ")"
    )


async def fetch_matching_records(normalized_username: str) -> list[dict[str, Any]]:
    pat, base_id = get_airtable_credentials()
    if not pat or not base_id:
        raise RuntimeError("Airtable credentials are not configured")

    formula = filter_by_telegram_formula(normalized_username)
    headers = {"Authorization": f"Bearer {pat}"}
    out: list[dict[str, Any]] = []
    offset: str | None = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            params: dict[str, str | int] = {
                "filterByFormula": formula,
                "pageSize": 100,
            }
            if offset:
                params["offset"] = offset

            url = f"{AIRTABLE_API}/{base_id}/{STERILIZATION_TABLE}"
            r = await client.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
            out.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break

    return out
