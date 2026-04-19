"""Format Airtable field values and record lists for Telegram messages."""

from __future__ import annotations

from typing import Any


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


def build_summary_text(records: list[dict[str, Any]], compact: bool = False) -> str:
    blocks: list[str] = []
    for i, rec in enumerate(records, start=1):
        fields = rec.get("fields") or {}
        rec_id = fields.get("id")
        if rec_id is None:
            rec_id = rec.get("id", "—")
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
