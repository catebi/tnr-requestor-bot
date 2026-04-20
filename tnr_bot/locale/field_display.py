"""
Display-only translations for Airtable field values (single select / text).

Keys must match Airtable API strings exactly (see PRD). Queries and lookups use raw values;
only user-visible strings go through :func:`display_field_value`.
"""

from __future__ import annotations

from typing import Any

from tnr_bot.locale import normalize_locale

STATUS_FIELD = "status"

# field_name -> stored_value -> locale -> display string
DISPLAY_MAPS: dict[str, dict[str, dict[str, str]]] = {
    STATUS_FIELD: {
        "Новая заявка": {
            "en": "New request",
            "ru": "Новая заявка",
            "ka": "ახალი მიმართვა",
        },
        "Коммуникация с заявителем": {
            "en": "Communicating with requestor",
            "ru": "Коммуникация с заявителем",
            "ka": "კომუნიკაცია მიმართვასთან",
        },
        "Стерилизация назначена": {
            "en": "Sterilisation scheduled",
            "ru": "Стерилизация назначена",
            "ka": "სტერილიზაცია დანიშნულია",
        },
        "Стерилизация перенесена": {
            "en": "Sterilisation rescheduled",
            "ru": "Стерилизация перенесена",
            "ka": "სტერილიზაცია გადაინიშნა",
        },
        "На пути в котодом": {
            "en": "On the way to the cat flat",
            "ru": "На пути в котодом",
            "ka": "გზაშია კატების ბინისკენ",
        },
        "Возвращена заявителю": {
            "en": "Returned to requestor",
            "ru": "Возвращена заявителю",
            "ka": "დაუბრუნდა მიმართვას",
        },
        "Стерилизация отменена": {
            "en": "Sterilisation cancelled",
            "ru": "Стерилизация отменена",
            "ka": "სტერილიზაცია გაუქმებულია",
        },
        "принята в кк": {
            "en": "Accepted at cat flat",
            "ru": "принята в кк",
            "ka": "მიღებულია კატების ბინაში",
        },
        "Заявитель перестал отвечать": {
            "en": "Requestor stopped responding",
            "ru": "Заявитель перестал отвечать",
            "ka": "მიმართვამ გაჩერდა პასუხის გარეშე",
        },
    },
}


def _map_row_for_value(
    field_name: str,
    stored_key: str,
) -> dict[str, str] | None:
    fm = DISPLAY_MAPS.get(field_name)
    if not fm:
        return None
    if stored_key in fm:
        return fm[stored_key]
    sk = stored_key.casefold()
    for mk, row in fm.items():
        if mk.casefold() == sk:
            return row
    return None


def display_field_value(field_name: str, raw: Any, locale: str) -> str:
    """
    Return a user-facing string for ``raw`` in ``field_name`` for ``locale``.

    Falls back to :func:`tnr_bot.utils.formatting.format_field` when the field has no map
    or the value is unknown (lazy import avoids circular imports with ``formatting``).
    """
    from tnr_bot.utils.formatting import format_field

    loc = normalize_locale(locale)
    base = format_field(raw)

    fm = DISPLAY_MAPS.get(field_name)
    if not fm:
        return base

    if raw is None:
        return base

    if isinstance(raw, list):
        if not raw:
            return base
        parts_out: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                inner = item.get("name") or item.get("email")
                if inner is not None:
                    parts_out.append(
                        display_field_value(field_name, inner, locale)
                    )
                else:
                    parts_out.append(display_field_value(field_name, str(item), locale))
            else:
                parts_out.append(display_field_value(field_name, item, locale))
        return ", ".join(parts_out) if parts_out else base

    if isinstance(raw, dict):
        inner = raw.get("name") or raw.get("email")
        if inner is not None:
            return display_field_value(field_name, inner, locale)
        return base

    key = str(raw).strip()
    if not key:
        return base

    row = _map_row_for_value(field_name, key)
    if not row:
        return base

    return row.get(loc) or row.get("en") or base
