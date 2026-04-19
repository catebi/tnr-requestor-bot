"""Attach all handlers to the Application. One place to merge work from multiple branches."""

from __future__ import annotations

from telegram.ext import Application, CommandHandler

from tnr_bot.handlers.start import myrequests_cmd, start_cmd


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("myrequests", myrequests_cmd))
