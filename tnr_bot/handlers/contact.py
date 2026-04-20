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
    sterilization_created_field,
    sterilization_language_field,
)
from tnr_bot.locale import locale_from_telegram_language, resolve_effective_locale, t
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

    tg_lang = update.effective_user.language_code
    username = update.effective_user.username
    if not username:
        loc = locale_from_telegram_language(tg_lang)
        await update.message.reply_text(t("error.need_public_username_contact", loc))
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

    if not _any_operator_assigned(records):
        await update.message.reply_text(
            t("contact.no_operator_yet", locale, fallback=CONTACT_FALLBACK_TELEGRAM)
        )
        return

    try:
        operator_records = await fetch_all_operator_records()
    except httpx.HTTPStatusError as e:
        logger.exception("Airtable operators table HTTP error: %s", e.response.text)
        await update.message.reply_text(t("error.operators_unavailable", locale))
        return
    except Exception:
        logger.exception("Unexpected error while fetching operators table")
        await update.message.reply_text(t("error.generic", locale))
        return

    directory = build_operator_directory(
        operator_records,
        match_field=operators_match_field(),
        telegram_field=operators_telegram_field(),
    )
    body = format_contact_list_text(records, directory, locale=locale)
    text = t("contact.header", locale) + body

    if len(text) <= MessageLimit.MAX_TEXT_LENGTH:
        await update.message.reply_text(text)
        return

    chunk_size = MessageLimit.MAX_TEXT_LENGTH
    for start in range(0, len(text), chunk_size):
        part = text[start : start + chunk_size]
        await update.message.reply_text(part)
