"""/start and /myrequests — list sterilization requests for the user's Telegram handle."""

from __future__ import annotations

import logging

import httpx
from telegram import Update
from telegram.constants import MessageLimit
from telegram.ext import ContextTypes

from tnr_bot.integrations.airtable import (
    fetch_all_operator_records,
    fetch_matching_records,
    sterilization_created_field,
    sterilization_language_field,
)
from tnr_bot.integrations.airtable_write import patch_telegram_chat_id_on_records
from tnr_bot.locale import locale_from_telegram_language, resolve_effective_locale, t
from tnr_bot.utils.formatting import build_operator_directory, build_summary_text_auto_compact
from tnr_bot.utils.telegram_identity import normalize_handle

logger = logging.getLogger(__name__)


async def reply_with_matching_requests(update: Update) -> None:
    """Fetch Airtable rows for this Telegram username and reply with id, dates, status, operator."""
    if update.effective_user is None or update.message is None:
        return

    tg_lang = update.effective_user.language_code
    username = update.effective_user.username
    if not username:
        loc = locale_from_telegram_language(tg_lang)
        await update.message.reply_text(t("error.need_public_username_start", loc))
        return

    normalized = normalize_handle(username)
    lang_f = sterilization_language_field()
    created_f = sterilization_created_field()

    try:
        records = await fetch_matching_records(normalized, sort_newest_first=True)
    except httpx.HTTPStatusError as e:
        logger.exception("Airtable HTTP error: %s", e.response.text)
        await update.message.reply_text(
            t("error.airtable_unavailable", locale_from_telegram_language(tg_lang))
        )
        return
    except Exception:
        logger.exception("Unexpected error while fetching Airtable records")
        await update.message.reply_text(t("error.generic", locale_from_telegram_language(tg_lang)))
        return

    locale = resolve_effective_locale(
        tg_lang,
        records,
        language_field=lang_f,
        created_field=created_f,
        records_newest_first=True,
    )

    if not records:
        await update.message.reply_text(t("no_requests", locale, username=username))
        return

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
            "Could not sync telegram_chat_id to Airtable (check PAT write scope and telegram_chat_id field)"
        )

    operator_directory = None
    try:
        op_recs = await fetch_all_operator_records()
        operator_directory = build_operator_directory(op_recs)
    except Exception:
        logger.warning("Could not load operators table for /start listing operator names", exc_info=True)

    text = build_summary_text_auto_compact(
        records, operator_directory=operator_directory, locale=locale
    )

    if len(text) <= MessageLimit.MAX_TEXT_LENGTH:
        await update.message.reply_text(text)
        return

    chunk_size = MessageLimit.MAX_TEXT_LENGTH
    for start in range(0, len(text), chunk_size):
        part = text[start : start + chunk_size]
        await update.message.reply_text(part)


async def start_or_myrequests_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_with_matching_requests(update)
