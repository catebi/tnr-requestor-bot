"""Attach all handlers to the Application. One place to merge work from multiple branches."""

from __future__ import annotations

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from tnr_bot.handlers.contact import contact_cmd
from tnr_bot.handlers.language import language_callback, language_cmd
from tnr_bot.handlers.start import start_or_myrequests_cmd


def register_handlers(app: Application) -> None:
    app.add_handler(CallbackQueryHandler(language_callback, pattern=r"^lang:(en|ru|ka)$"))
    app.add_handler(CommandHandler(["start", "myrequests"], start_or_myrequests_cmd))
    app.add_handler(CommandHandler("contact", contact_cmd))
    app.add_handler(CommandHandler("language", language_cmd))
