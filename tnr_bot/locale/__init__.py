"""Localization: English, Russian, Georgian."""

from __future__ import annotations

import os
from typing import Any

from tnr_bot.locale.strings import STRINGS

SUPPORTED_LOCALES = frozenset({"en", "ru", "ka"})

# Native names for inline keyboard labels and confirmation (always these scripts).
LANGUAGE_NATIVE_NAME: dict[str, str] = {
    "en": "English",
    "ru": "Русский",
    "ka": "ქართული",
}


def normalize_locale(code: str | None) -> str:
    """Map arbitrary locale string to en, ru, or ka."""
    if not code or not str(code).strip():
        return "en"
    base = str(code).strip().split("-")[0].lower()
    if base in SUPPORTED_LOCALES:
        return base
    return "en"


def locale_from_telegram_language(language_code: str | None) -> str:
    """Use Telegram client language (``User.language_code``)."""
    return normalize_locale(language_code)


def locale_from_airtable_value(raw: Any) -> str | None:
    """
    Map Airtable ``language`` cell (single line text, single select, etc.) to ``en`` / ``ru`` / ``ka``.
    Returns ``None`` when empty or unknown so callers can fall back to Telegram language.
    """
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        first = raw[0]
        if isinstance(first, dict):
            raw = first.get("name") or first.get("email") or str(first)
        else:
            raw = first
    s = str(raw).strip()
    if not s:
        return None
    low = s.casefold()
    if low in ("en", "english", "eng"):
        return "en"
    if low in ("ru", "rus", "russian", "русский"):
        return "ru"
    if low in ("ka", "kat", "georgian") or s == "ქართული":
        return "ka"
    # Common alternate code for Georgian in forms
    if low == "ge":
        return "ka"
    if low in SUPPORTED_LOCALES:
        return low
    return None


def pick_latest_sterilization_record(
    records: list[dict[str, Any]],
    *,
    created_field: str,
) -> dict[str, Any] | None:
    """When API sort is unavailable, pick the row with the greatest ``created_field`` string."""
    if not records:
        return None

    def sort_key(rec: dict[str, Any]) -> str:
        v = (rec.get("fields") or {}).get(created_field)
        if v is None:
            return ""
        return str(v)

    return max(records, key=sort_key)


def resolve_effective_locale(
    telegram_language_code: str | None,
    records: list[dict[str, Any]],
    *,
    language_field: str,
    created_field: str,
    records_newest_first: bool,
) -> str:
    """
    Prefer ``language`` on the **latest** sterilization row (by ``created_field``); otherwise
    Telegram UI language (``en`` / ``ru`` / ``ka`` with fallback to English).
    """
    tg = locale_from_telegram_language(telegram_language_code)
    if not records:
        return tg
    latest = (
        records[0]
        if records_newest_first
        else pick_latest_sterilization_record(records, created_field=created_field)
    )
    if latest is None:
        return tg
    raw = (latest.get("fields") or {}).get(language_field)
    at = locale_from_airtable_value(raw)
    return at if at is not None else tg


def default_notify_locale() -> str:
    """Locale for notify webhook when client not available (env ``NOTIFY_DEFAULT_LOCALE``)."""
    return normalize_locale(os.getenv("NOTIFY_DEFAULT_LOCALE"))


def t(key: str, locale: str, **kwargs: Any) -> str:
    """Translate ``key``; fall back to English string; then to ``key``."""
    loc = normalize_locale(locale)
    table = STRINGS.get(loc) or STRINGS["en"]
    template = table.get(key)
    if template is None:
        template = STRINGS["en"].get(key) or key
    try:
        return template.format(**kwargs) if kwargs else template
    except (KeyError, ValueError):
        return template
