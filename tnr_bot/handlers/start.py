"""/start — list sterilization requests for the user's Telegram handle."""

from __future__ import annotations

import logging

import httpx
from telegram import Update
from telegram.constants import MessageLimit
from telegram.ext import ContextTypes

from tnr_bot.integrations.airtable import fetch_matching_records
from tnr_bot.utils.formatting import build_summary_text
from tnr_bot.utils.telegram_identity import normalize_handle

logger = logging.getLogger(__name__)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    username = update.effective_user.username
    if not username:
        await update.message.reply_text(
            "Set a public Telegram username in Settings so we can match your sterilization "
            "form. Then send /start again."
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

    text = build_summary_text(records, compact=False)
    if len(text) > MessageLimit.MAX_TEXT_LENGTH:
        text = build_summary_text(records, compact=True)

    if len(text) <= MessageLimit.MAX_TEXT_LENGTH:
        await update.message.reply_text(text)
        return

    chunk_size = MessageLimit.MAX_TEXT_LENGTH
    for start in range(0, len(text), chunk_size):
        part = text[start : start + chunk_size]
        await update.message.reply_text(part)
