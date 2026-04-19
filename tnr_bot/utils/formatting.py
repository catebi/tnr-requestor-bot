"""Format Airtable field values and record lists for Telegram messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from telegram.constants import MessageLimit


def format_field(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
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


def format_operator_field_for_summary(raw: Any) -> str:
    """
    ``operator`` may be a single-select label (string) or a linked record field (list of ``rec…`` ids).
    We do not load the ``operators`` table here; linked assignments are summarized without raw record ids.
    """
    if raw is None:
        return "—"
    if isinstance(raw, list):
        if not raw:
            return "—"
        if all(isinstance(x, str) and x.startswith("rec") for x in raw):
            return "assigned"
        return format_field(raw)
    if isinstance(raw, str) and raw.startswith("rec"):
        return "assigned"
    return format_field(raw)


def build_summary_text(records: list[dict[str, Any]], compact: bool = False) -> str:
    blocks: list[str] = []
    for i, rec in enumerate(records, start=1):
        fields = rec.get("fields") or {}
        rec_id = _record_display_id(rec)
        op_disp = format_operator_field_for_summary(fields.get("operator"))
        if compact:
            blocks.append(
                f"{i}. id={format_field(rec_id)} | created_date={format_field(fields.get('created_date'))} | "
                f"status={format_field(fields.get('status'))} | operator={op_disp}"
            )
        else:
            line = (
                f"{i}. id: {format_field(rec_id)}\n"
                f"   created_date: {format_field(fields.get('created_date'))}\n"
                f"   status: {format_field(fields.get('status'))}\n"
                f"   operator: {op_disp}"
            )
            blocks.append(line)
    sep = "\n" if compact else "\n\n"
    return sep.join(blocks)


def build_summary_text_auto_compact(records: list[dict[str, Any]]) -> str:
    """Use non-compact layout, then compact, so a single string fits one Telegram message when possible."""
    max_len = MessageLimit.MAX_TEXT_LENGTH
    text = build_summary_text(records, compact=False)
    if len(text) > max_len:
        text = build_summary_text(records, compact=True)
    return text


# When no operator is assigned on any request, point users here (exact handle per product).
CONTACT_FALLBACK_TELEGRAM = "@religofsil"


@dataclass(frozen=True)
class OperatorDirectory:
    """Maps ``operators`` rows to Telegram handles and display labels."""

    telegram_by_record_id: dict[str, str]
    """Operator row id ``rec…`` -> ``@handle``."""

    label_by_record_id: dict[str, str]
    """Operator row id -> display name (``OPERATORS_MATCH_FIELD``)."""

    telegram_by_label: dict[str, str]
    """Lowercased single-select label -> ``@handle`` (when ``operator`` is not a link)."""


def build_operator_directory(
    operator_records: list[dict[str, Any]],
    *,
    match_field: str,
    telegram_field: str,
) -> OperatorDirectory:
    """Build lookups from all rows in the ``operators`` table."""
    by_rec_tg: dict[str, str] = {}
    by_rec_lbl: dict[str, str] = {}
    by_lbl_tg: dict[str, str] = {}

    for rec in operator_records:
        rid = rec.get("id")
        if not rid or not isinstance(rid, str):
            continue
        fields = rec.get("fields") or {}
        label = fields.get(match_field)
        raw_tg = fields.get(telegram_field)
        tg = _normalize_telegram_handle(raw_tg)
        if tg:
            by_rec_tg[rid] = tg
        if label is not None and str(label).strip():
            by_rec_lbl[rid] = str(label).strip()
            if tg:
                by_lbl_tg[str(label).strip().casefold()] = tg

    return OperatorDirectory(
        telegram_by_record_id=by_rec_tg,
        label_by_record_id=by_rec_lbl,
        telegram_by_label=by_lbl_tg,
    )


def _operator_field_rec_ids(raw: Any) -> list[str]:
    """Linked ``operator`` fields return a list of ``rec…`` ids."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if isinstance(x, str) and str(x).strip().startswith("rec")]
    if isinstance(raw, str) and raw.strip().startswith("rec"):
        return [raw.strip()]
    return []


def format_contact_list_text(records: list[dict[str, Any]], directory: OperatorDirectory) -> str:
    """One bullet per request: numeric id, status, operator name(s) and Telegram."""
    lines: list[str] = []
    for rec in records:
        fields = rec.get("fields") or {}
        rid = format_field(_record_display_id(rec))
        status = format_field(fields.get("status"))
        op_raw = fields.get("operator")

        rec_ids = _operator_field_rec_ids(op_raw)
        if rec_ids:
            parts: list[str] = []
            for orid in rec_ids:
                name = directory.label_by_record_id.get(orid) or "Operator"
                tg = directory.telegram_by_record_id.get(orid)
                if tg:
                    parts.append(f"{name} {tg}")
                else:
                    parts.append(f"{name} (no Telegram in directory)")
            lines.append(f"• id {rid} · {status} · {' · '.join(parts)}")
            continue

        # Single select or plain text label
        if op_raw is None or not str(op_raw).strip():
            lines.append(f"• id {rid} · {status} · operator: not assigned yet")
            continue
        label = str(op_raw).strip()
        tg = directory.telegram_by_label.get(label.casefold())
        if tg:
            lines.append(f"• id {rid} · {status} · {label} · {tg}")
        else:
            lines.append(
                f"• id {rid} · {status} · {label} · (no Telegram handle in the operators directory)"
            )
    return "\n".join(lines)


def _build_notify_message_with_prefix(record: dict[str, Any], prefix: str) -> str:
    """Prefix plus request summary; compact and truncate to one Telegram message."""
    max_len = MessageLimit.MAX_TEXT_LENGTH
    for compact in (False, True):
        body = build_summary_text([record], compact=compact)
        text = prefix + body
        if len(text) <= max_len:
            return text
    return (prefix + build_summary_text([record], compact=True))[:max_len]


def build_notify_new_request_message(record: dict[str, Any]) -> str:
    """Webhook: new row (or default notify type)."""
    return _build_notify_message_with_prefix(record, "New sterilization request:\n\n")


def build_notify_operator_assigned_message(record: dict[str, Any]) -> str:
    """Webhook: ``operator`` field was set or changed."""
    return _build_notify_message_with_prefix(
        record,
        "An operator was assigned to your sterilization request:\n\n",
    )


def build_notify_status_changed_message(record: dict[str, Any]) -> str:
    """Webhook: ``status`` field was updated."""
    return _build_notify_message_with_prefix(
        record,
        "Your sterilization request status was updated:\n\n",
    )
