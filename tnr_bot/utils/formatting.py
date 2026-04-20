"""Format Airtable field values and record lists for Telegram messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from telegram.constants import MessageLimit

from tnr_bot.integrations.airtable import OPERATORS_MATCH_FIELD, OPERATORS_TELEGRAM_FIELD
from tnr_bot.locale import t
from tnr_bot.locale.field_display import STATUS_FIELD, display_field_value


def _unwrap_airtable_cell(value: Any) -> Any:
    """
    Airtable may return single-select cells as ``{state, value, isStale, ...}``.
    Reduce to the scalar ``value`` for display and matching.
    """
    if isinstance(value, dict) and "value" in value:
        inner = value.get("value")
        if isinstance(inner, dict):
            return _unwrap_airtable_cell(inner)
        if inner is not None:
            return inner
    return value


def format_field(value: Any) -> str:
    if value is None:
        return "—"
    value = _unwrap_airtable_cell(value)
    if value is None:
        return "—"
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            item = _unwrap_airtable_cell(item)
            if isinstance(item, dict):
                parts.append(item.get("name") or item.get("email") or str(item))
            else:
                parts.append(str(item))
        return ", ".join(parts) if parts else "—"
    if isinstance(value, dict):
        return value.get("name") or value.get("email") or str(value)
    return str(value)


def _record_display_id(rec: dict[str, Any]) -> Any:
    """
    Prefer the human-facing request **id** field (autonumber / number on the form).
    Fall back to Airtable record id (``rec…``) only when that field is missing.
    """
    fields = rec.get("fields") or {}
    form_id = fields.get("id")
    if form_id is not None and str(form_id).strip() != "":
        return form_id
    return rec.get("id", "—")


def _normalize_telegram_handle(raw: Any) -> str | None:
    if raw is None or str(raw).strip() == "":
        return None
    handle = str(raw).strip()
    if not handle.startswith("@"):
        handle = "@" + handle.lstrip("@")
    return handle


def _operator_field_rec_ids(raw: Any) -> list[str]:
    """Linked ``operator`` fields return a list of ``rec…`` ids."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if isinstance(x, str) and str(x).strip().startswith("rec")]
    if isinstance(raw, str) and raw.strip().startswith("rec"):
        return [raw.strip()]
    return []


# When no operator is assigned on any request, point users here (exact handle per product).
CONTACT_FALLBACK_TELEGRAM = "@religofsil"

# Fixed ``operators`` table fields for localized display names (not configurable).
OPERATOR_FIELD_NAME_EN = "operator_name_en"
OPERATOR_FIELD_NAME_RU = "operator_name_ru"
OPERATOR_FIELD_NAME_KA = "operator_name_ka"


@dataclass(frozen=True)
class OperatorDirectory:
    """Maps ``operators`` rows to Telegram handles and display labels."""

    telegram_by_record_id: dict[str, str]
    """Operator row id ``rec…`` -> ``@handle``."""

    label_by_record_id: dict[str, str]
    """Operator row id -> canonical match label (``operator_name`` on ``operators``)."""

    telegram_by_label: dict[str, str]
    """Lowercased single-select label -> ``@handle`` (when ``operator`` is not a link)."""

    localized_by_record_id: dict[str, dict[str, str]]
    """Operator row id -> ``en`` / ``ru`` / ``ka`` display strings from ``operators``."""

    localized_by_label_casefold: dict[str, dict[str, str]]
    """Lowercased single-select label -> per-locale display strings (same source)."""


def _operator_row_localized_names(
    fields: dict[str, Any],
) -> dict[str, str]:
    """Build ``en``/``ru``/``ka`` strings; empty localized cells fall back to ``operator_name``."""
    base = str(_unwrap_airtable_cell(fields.get(OPERATORS_MATCH_FIELD)) or "").strip()
    out: dict[str, str] = {}
    for loc, fname in (
        ("en", OPERATOR_FIELD_NAME_EN),
        ("ru", OPERATOR_FIELD_NAME_RU),
        ("ka", OPERATOR_FIELD_NAME_KA),
    ):
        raw = _unwrap_airtable_cell(fields.get(fname))
        if raw is not None and str(raw).strip():
            out[loc] = str(raw).strip()
        elif base:
            out[loc] = base
        else:
            out[loc] = "—"
    return out


def build_operator_directory(
    operator_records: list[dict[str, Any]],
) -> OperatorDirectory:
    """Build lookups from all rows in the ``operators`` table (fixed field names in ``airtable``)."""
    by_rec_tg: dict[str, str] = {}
    by_rec_lbl: dict[str, str] = {}
    by_lbl_tg: dict[str, str] = {}
    by_rec_loc: dict[str, dict[str, str]] = {}
    by_lbl_loc: dict[str, dict[str, str]] = {}

    for rec in operator_records:
        rid = rec.get("id")
        if not rid or not isinstance(rid, str):
            continue
        fields = rec.get("fields") or {}
        label = _unwrap_airtable_cell(fields.get(OPERATORS_MATCH_FIELD))
        raw_tg = fields.get(OPERATORS_TELEGRAM_FIELD)
        tg = _normalize_telegram_handle(raw_tg)
        if tg:
            by_rec_tg[rid] = tg
        if label is not None and str(label).strip():
            canon = str(label).strip()
            by_rec_lbl[rid] = canon
            if tg:
                by_lbl_tg[canon.casefold()] = tg
            loc_row = _operator_row_localized_names(fields)
            by_rec_loc[rid] = loc_row
            by_lbl_loc[canon.casefold()] = loc_row

    return OperatorDirectory(
        telegram_by_record_id=by_rec_tg,
        label_by_record_id=by_rec_lbl,
        telegram_by_label=by_lbl_tg,
        localized_by_record_id=by_rec_loc,
        localized_by_label_casefold=by_lbl_loc,
    )


def get_operator_display_name(
    directory: OperatorDirectory | None,
    locale: str,
    *,
    record_id: str | None = None,
    raw_single_select_label: str | None = None,
) -> str:
    """
    User-facing operator name for ``locale`` using ``operators`` localized columns.

    Matching on ``sterilization_request`` still uses the canonical single-select / link; this only affects display.
    """
    from tnr_bot.locale import normalize_locale

    loc = normalize_locale(locale)
    if directory is None:
        return format_field(raw_single_select_label) if raw_single_select_label is not None else "—"

    if record_id:
        row = directory.localized_by_record_id.get(record_id)
        if row:
            return row.get(loc) or row.get("en") or directory.label_by_record_id.get(record_id) or record_id
        return directory.label_by_record_id.get(record_id) or record_id

    if raw_single_select_label is None:
        return "—"
    raw_single_select_label = _unwrap_airtable_cell(raw_single_select_label)
    s = str(raw_single_select_label).strip()
    if not s:
        return "—"
    row = directory.localized_by_label_casefold.get(s.casefold())
    if row:
        return row.get(loc) or row.get("en") or s
    return s


def format_operator_for_summary_line(
    raw: Any,
    directory: OperatorDirectory | None,
    *,
    locale: str = "en",
) -> str:
    """
    Human-readable operator for list/notify: linked ``rec…`` ids resolve via ``operators``;
    single-select stays as the label string.
    """
    if raw is None:
        return "—"
    rec_ids = _operator_field_rec_ids(raw)
    if rec_ids:
        if directory is None:
            return t("summary.operator_linked_fallback", locale)
        parts: list[str] = []
        for oid in rec_ids:
            parts.append(get_operator_display_name(directory, locale, record_id=oid))
        return ", ".join(parts) if parts else "—"
    raw = _unwrap_airtable_cell(raw)
    s = str(raw).strip()
    if not s:
        return "—"
    return get_operator_display_name(directory, locale, raw_single_select_label=s)


def build_summary_text(
    records: list[dict[str, Any]],
    compact: bool = False,
    *,
    operator_directory: OperatorDirectory | None = None,
    locale: str = "en",
) -> str:
    lbl_id = t("summary.label_id", locale)
    lbl_cd = t("summary.label_created_date", locale)
    lbl_st = t("summary.label_status", locale)
    lbl_op = t("summary.label_operator", locale)
    blocks: list[str] = []
    for i, rec in enumerate(records, start=1):
        fields = rec.get("fields") or {}
        rec_id = _record_display_id(rec)
        op_disp = format_operator_for_summary_line(
            fields.get("operator"), operator_directory, locale=locale
        )
        if compact:
            blocks.append(
                f"{i}. {lbl_id}={format_field(rec_id)} | {lbl_cd}={format_field(fields.get('created_date'))} | "
                f"{lbl_st}={display_field_value(STATUS_FIELD, fields.get('status'), locale)} | {lbl_op}={op_disp}"
            )
        else:
            line = (
                f"{i}. {lbl_id}: {format_field(rec_id)}\n"
                f"   {lbl_cd}: {format_field(fields.get('created_date'))}\n"
                f"   {lbl_st}: {display_field_value(STATUS_FIELD, fields.get('status'), locale)}\n"
                f"   {lbl_op}: {op_disp}"
            )
            blocks.append(line)
    sep = "\n" if compact else "\n\n"
    return sep.join(blocks)


def build_summary_text_auto_compact(
    records: list[dict[str, Any]],
    *,
    operator_directory: OperatorDirectory | None = None,
    locale: str = "en",
) -> str:
    """Use non-compact layout, then compact, so a single string fits one Telegram message when possible."""
    max_len = MessageLimit.MAX_TEXT_LENGTH
    text = build_summary_text(
        records, compact=False, operator_directory=operator_directory, locale=locale
    )
    if len(text) > max_len:
        text = build_summary_text(
            records, compact=True, operator_directory=operator_directory, locale=locale
        )
    return text


def format_contact_list_text(
    records: list[dict[str, Any]], directory: OperatorDirectory, *, locale: str = "en"
) -> str:
    """One bullet per request: numeric id, status, operator name(s) and Telegram."""
    op_placeholder = t("contact.operator_placeholder", locale)
    lines: list[str] = []
    for rec in records:
        fields = rec.get("fields") or {}
        rid = format_field(_record_display_id(rec))
        status = display_field_value(STATUS_FIELD, fields.get("status"), locale)
        op_raw = fields.get("operator")

        rec_ids = _operator_field_rec_ids(op_raw)
        if rec_ids:
            parts: list[str] = []
            for orid in rec_ids:
                if orid not in directory.label_by_record_id:
                    name_disp = op_placeholder
                else:
                    name_disp = get_operator_display_name(directory, locale, record_id=orid)
                tg = directory.telegram_by_record_id.get(orid)
                if tg:
                    parts.append(f"{name_disp} {tg}")
                else:
                    parts.append(t("contact.part_no_telegram", locale, name=name_disp))
            lines.append(
                t("contact.line_linked", locale, rid=rid, status=status, parts=" · ".join(parts))
            )
            continue

        # Single select or plain text label
        if op_raw is None:
            lines.append(t("contact.operator_not_assigned", locale, rid=rid, status=status))
            continue
        op_unwrapped = _unwrap_airtable_cell(op_raw)
        if op_unwrapped is None or not str(op_unwrapped).strip():
            lines.append(t("contact.operator_not_assigned", locale, rid=rid, status=status))
            continue
        label = str(op_unwrapped).strip()
        tg = directory.telegram_by_label.get(label.casefold())
        label_disp = get_operator_display_name(directory, locale, raw_single_select_label=label)
        if tg:
            lines.append(
                t(
                    "contact.line_label_tg",
                    locale,
                    rid=rid,
                    status=status,
                    label=label_disp,
                    tg=tg,
                )
            )
        else:
            lines.append(
                t(
                    "contact.no_handle_directory",
                    locale,
                    rid=rid,
                    status=status,
                    label=label_disp,
                )
            )
    return "\n".join(lines)


def _build_notify_message_with_prefix(
    record: dict[str, Any],
    prefix: str,
    *,
    operator_directory: OperatorDirectory | None = None,
    locale: str = "en",
) -> str:
    """Prefix plus request summary; compact and truncate to one Telegram message."""
    max_len = MessageLimit.MAX_TEXT_LENGTH
    for compact in (False, True):
        body = build_summary_text(
            [record], compact=compact, operator_directory=operator_directory, locale=locale
        )
        text = prefix + body
        if len(text) <= max_len:
            return text
    return (
        prefix
        + build_summary_text(
            [record], compact=True, operator_directory=operator_directory, locale=locale
        )
    )[:max_len]


def build_notify_new_request_message(
    record: dict[str, Any],
    *,
    operator_directory: OperatorDirectory | None = None,
    locale: str = "en",
) -> str:
    """Webhook: new row (or default notify type)."""
    return _build_notify_message_with_prefix(
        record,
        t("notify.prefix_new_request", locale),
        operator_directory=operator_directory,
        locale=locale,
    )


def build_notify_operator_assigned_message(
    record: dict[str, Any],
    *,
    operator_directory: OperatorDirectory | None = None,
    locale: str = "en",
) -> str:
    """Webhook: ``operator`` field was set or changed."""
    return _build_notify_message_with_prefix(
        record,
        t("notify.prefix_operator_assigned", locale),
        operator_directory=operator_directory,
        locale=locale,
    )


def build_notify_status_changed_message(
    record: dict[str, Any],
    *,
    operator_directory: OperatorDirectory | None = None,
    locale: str = "en",
) -> str:
    """Webhook: ``status`` field was updated."""
    return _build_notify_message_with_prefix(
        record,
        t("notify.prefix_status_changed", locale),
        operator_directory=operator_directory,
        locale=locale,
    )
