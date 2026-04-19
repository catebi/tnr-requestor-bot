"""Format Airtable field values and record lists for Telegram messages."""

from __future__ import annotations

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
    Prefer Airtable API record id (``rec…``) so we never confuse it with a field also named ``id``.
    """
    rid = rec.get("id")
    if rid is not None:
        return rid
    fields = rec.get("fields") or {}
    return fields.get("id", "—")


def build_summary_text(records: list[dict[str, Any]], compact: bool = False) -> str:
    blocks: list[str] = []
    for i, rec in enumerate(records, start=1):
        fields = rec.get("fields") or {}
        rec_id = _record_display_id(rec)
        if compact:
            blocks.append(
                f"{i}. id={format_field(rec_id)} | created_date={format_field(fields.get('created_date'))} | "
                f"status={format_field(fields.get('status'))} | operator={format_field(fields.get('operator'))}"
            )
        else:
            line = (
                f"{i}. id: {format_field(rec_id)}\n"
                f"   created_date: {format_field(fields.get('created_date'))}\n"
                f"   status: {format_field(fields.get('status'))}\n"
                f"   operator: {format_field(fields.get('operator'))}"
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


def build_notify_new_request_message(record: dict[str, Any]) -> str:
    """
    One Telegram message for a webhook: prefix plus summary, compact and truncate as needed.
    """
    max_len = MessageLimit.MAX_TEXT_LENGTH
    prefix = "New sterilization request:\n\n"
    for compact in (False, True):
        body = build_summary_text([record], compact=compact)
        text = prefix + body
        if len(text) <= max_len:
            return text
    return (prefix + build_summary_text([record], compact=True))[:max_len]
