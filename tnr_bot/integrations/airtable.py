"""Sterilization request records in Airtable."""

from __future__ import annotations

from typing import Any

import httpx

from tnr_bot.config import get_airtable_credentials

AIRTABLE_API = "https://api.airtable.com/v0"
STERILIZATION_TABLE = "sterilization_request"


def sterilization_table_url(base_id: str) -> str:
    """Collection URL for list and PATCH on ``sterilization_request``."""
    return f"{AIRTABLE_API}/{base_id}/{STERILIZATION_TABLE}"


def sterilization_record_url(base_id: str, record_id: str) -> str:
    """Single-record URL (GET one row by ``rec…`` id)."""
    return f"{sterilization_table_url(base_id)}/{record_id}"


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

            url = sterilization_table_url(base_id)
            r = await client.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
            out.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break

    return out


async def fetch_record_by_id(record_id: str) -> dict[str, Any] | None:
    """Return one record by Airtable record id (rec…), or None if 404."""
    pat, base_id = get_airtable_credentials()
    if not pat or not base_id:
        raise RuntimeError("Airtable credentials are not configured")

    headers = {"Authorization": f"Bearer {pat}"}
    url = sterilization_record_url(base_id, record_id)

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


def extract_telegram_chat_id(fields: dict[str, Any]) -> int | None:
    """Read numeric telegram_chat_id from Airtable fields (number or string)."""
    raw = fields.get("telegram_chat_id")
    if raw is None or raw == "":
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


async def resolve_telegram_chat_id_for_notify(
    record: dict[str, Any], normalized_handle: str
) -> int | None:
    """
    Prefer chat_id on this record; else any matching row by handle with telegram_chat_id set.
    """
    fields = record.get("fields") or {}
    cid = extract_telegram_chat_id(fields)
    if cid is not None:
        return cid

    matches = await fetch_matching_records(normalized_handle)
    for m in matches:
        cid = extract_telegram_chat_id(m.get("fields") or {})
        if cid is not None:
            return cid
    return None
