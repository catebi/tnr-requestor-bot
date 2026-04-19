"""Build the Telegram Application and start polling or webhook transport."""

from __future__ import annotations

import logging
import os

from telegram.ext import Application

from tnr_bot.config import get_airtable_credentials
from tnr_bot.handlers.register import register_handlers
from tnr_bot.runtime.transport import run_application

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def create_application() -> Application:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")

    pat, base_id = get_airtable_credentials()
    if not pat or not base_id:
        raise SystemExit(
            "Airtable credentials missing: set AIRTABLE_PAT / AIRTABLE_BASE_ID "
            "(or AIRTABLE_*_DEV when ENVIRONMENT=dev)"
        )

    app = Application.builder().token(token).build()
    register_handlers(app)
    return app


def main() -> None:
    app = create_application()
    transport = os.getenv("BOT_TRANSPORT", "polling")
    run_application(app, transport)


if __name__ == "__main__":
    main()
