"""/contact — show request ids, statuses, and operator Telegram handles."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from telegram import Update
from telegram.constants import MessageLimit
from telegram.ext import ContextTypes

from tnr_bot.integrations.airtable import (
    fetch_all_operator_records,
    fetch_matching_records,
    operators_match_field,
    operators_telegram_field,
)
from tnr_bot.utils.formatting import (
    CONTACT_FALLBACK_TELEGRAM,
    build_operator_directory,
    format_contact_list_text,
)
from tnr_bot.utils.telegram_identity import normalize_handle

logger = logging.getLogger(__name__)


def _any_operator_assigned(records: list[dict[str, Any]]) -> bool:
    for rec in records:
        op = (rec.get("fields") or {}).get("operator")
        if op is None:
            continue
        if isinstance(op, list):
            if len(op) > 0:
                return True
            continue
        if str(op).strip():
            return True
    return False


async def contact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    username = update.effective_user.username
    if not username:
        await update.message.reply_text(
            "Set a public Telegram username in Settings so we can match your sterilization "
            "form. Then send /contact again."
        )
        return

    normalized = normalize_handle(username)

    try:
        records = await fetch_matching_records(normalized)
    except httpx.HTTPStatusError as e:
        logger.exception("Airtable HTTP error: %s", e.response.text)
        await update.message.reply_text(
            "Could not reach the database. Check server configuration and try again later."
        )
        return
    except Exception:
        logger.exception("Unexpected error while fetching Airtable records")
        await update.message.reply_text("Something went wrong. Try again later.")
        return

    if not records:
        await update.message.reply_text(
            f"No sterilization requests found for @{username}. "
            f"Check that the form’s telegram field matches this handle (with or without @)."
        )
        return

    if not _any_operator_assigned(records):
        await update.message.reply_text(
            "No operator is assigned to your requests yet. "
            f"For questions, please write to {CONTACT_FALLBACK_TELEGRAM}."
        )
        return

    try:
        operator_records = await fetch_all_operator_records()
    except httpx.HTTPStatusError as e:
        logger.exception("Airtable operators table HTTP error: %s", e.response.text)
        await update.message.reply_text(
            "Could not load the operators directory. Try again later."
        )
        return
    except Exception:
        logger.exception("Unexpected error while fetching operators table")
        await update.message.reply_text("Something went wrong. Try again later.")
        return

    directory = build_operator_directory(
        operator_records,
        match_field=operators_match_field(),
        telegram_field=operators_telegram_field(),
    )
    body = format_contact_list_text(records, directory)
    text = "Here are your requests and operator contacts on Telegram:\n\n" + body

    if len(text) <= MessageLimit.MAX_TEXT_LENGTH:
        await update.message.reply_text(text)
        return

    chunk_size = MessageLimit.MAX_TEXT_LENGTH
    for start in range(0, len(text), chunk_size):
        part = text[start : start + chunk_size]
        await update.message.reply_text(part)
