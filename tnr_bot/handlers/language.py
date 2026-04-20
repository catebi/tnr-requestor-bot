"""/language — set preferred locale on all matching sterilization_request rows (field ``language``)."""

from __future__ import annotations

import logging
import re

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from tnr_bot.integrations.airtable import (
    fetch_matching_records,
    sterilization_created_field,
    sterilization_language_field,
)
from tnr_bot.integrations.airtable_write import patch_language_on_records
from tnr_bot.locale import (
    LANGUAGE_NATIVE_NAME,
    locale_from_telegram_language,
    resolve_effective_locale,
    t,
)
from tnr_bot.utils.telegram_identity import normalize_handle

logger = logging.getLogger(__name__)

_LANG_CB = re.compile(r"^lang:(en|ru|ka)$")


def _language_keyboard() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(LANGUAGE_NATIVE_NAME["en"], callback_data="lang:en"),
        InlineKeyboardButton(LANGUAGE_NATIVE_NAME["ru"], callback_data="lang:ru"),
        InlineKeyboardButton(LANGUAGE_NATIVE_NAME["ka"], callback_data="lang:ka"),
    ]
    return InlineKeyboardMarkup([row])


async def language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    tg = update.effective_user.language_code
    username = update.effective_user.username
    if not username:
        loc = locale_from_telegram_language(tg)
        await update.message.reply_text(t("error.need_public_username_language", loc))
        return

    normalized = normalize_handle(username)
    created_f = sterilization_created_field()
    lang_f = sterilization_language_field()

    try:
        records = await fetch_matching_records(normalized, sort_newest_first=True)
    except httpx.HTTPStatusError as e:
        logger.exception("Airtable HTTP error: %s", e.response.text)
        await update.message.reply_text(
            t("error.airtable_unavailable", locale_from_telegram_language(tg))
        )
        return
    except Exception:
        logger.exception("Unexpected error while fetching Airtable records")
        await update.message.reply_text(t("error.generic", locale_from_telegram_language(tg)))
        return

    locale = resolve_effective_locale(
        tg,
        records,
        language_field=lang_f,
        created_field=created_f,
        records_newest_first=True,
    )
    await update.message.reply_text(
        t("language.choose_prompt", locale), reply_markup=_language_keyboard()
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None or query.from_user is None:
        return

    m = _LANG_CB.match(query.data.strip())
    if not m:
        await query.answer()
        return

    chosen = m.group(1)
    tg = query.from_user.language_code
    username = query.from_user.username

    if not username:
        loc = locale_from_telegram_language(tg)
        await query.answer()
        if query.message:
            await query.message.reply_text(t("error.need_public_username_language", loc))
        return

    normalized = normalize_handle(username)
    created_f = sterilization_created_field()
    lang_f = sterilization_language_field()

    try:
        records = await fetch_matching_records(normalized, sort_newest_first=True)
    except Exception:
        logger.exception("language callback: fetch failed")
        loc = locale_from_telegram_language(tg)
        await query.answer()
        if query.message:
            await query.message.edit_text(t("error.airtable_unavailable", loc))
        return

    if not records:
        loc = resolve_effective_locale(
            tg,
            records,
            language_field=lang_f,
            created_field=created_f,
            records_newest_first=True,
        )
        await query.answer()
        if query.message:
            await query.message.edit_text(t("language.no_records", loc))
        return

    ids = [r["id"] for r in records if r.get("id")]
    ok = await patch_language_on_records(ids, chosen)

    loc = chosen
    native = LANGUAGE_NATIVE_NAME[chosen]
    await query.answer()
    if query.message:
        if ok:
            await query.message.edit_text(t("language.saved", loc, native=native))
        else:
            await query.message.edit_text(t("language.patch_failed", loc))
