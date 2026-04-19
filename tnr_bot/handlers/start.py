"""/start and /myrequests — list sterilization requests for the user's Telegram handle."""

from __future__ import annotations

import logging

import httpx
from telegram import Update
from telegram.constants import MessageLimit
from telegram.ext import ContextTypes

from tnr_bot.chat_store import remember_chat_id
from tnr_bot.integrations.airtable import fetch_matching_records
from tnr_bot.integrations.airtable_write import patch_telegram_chat_id_on_records, sync_chat_id_enabled
from tnr_bot.utils.formatting import build_summary_text
from tnr_bot.utils.telegram_identity import normalize_handle

logger = logging.getLogger(__name__)


async def reply_with_matching_requests(update: Update) -> None:
    """Fetch Airtable rows for this Telegram username and reply with id, dates, status, operator."""
    if update.effective_user is None or update.message is None:
        return

    username = update.effective_user.username
    if not username:
        await update.message.reply_text(
            "Set a public Telegram username in Settings so we can match your sterilization "
            "form. Then send /start or /myrequests again."
        )
        return

    normalized = normalize_handle(username)
    remember_chat_id(normalized, update.effective_chat.id)

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

    if sync_chat_id_enabled():
        chat_id = update.effective_chat.id
        try:
            synced = await patch_telegram_chat_id_on_records([r["id"] for r in records], chat_id)
            if synced:
                logger.info(
                    "Synced telegram_chat_id to %s matching sterilization_request row(s)",
                    len(records),
                )
        except Exception:
            logger.exception(
                "Could not sync telegram_chat_id to Airtable (check SYNC_TELEGRAM_CHAT_ID, "
                "PAT write scope, and telegram_chat_id field)"
            )

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


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_with_matching_requests(update)


async def myrequests_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_with_matching_requests(update)
