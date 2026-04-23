"""Run the bot with long polling (dev) or webhooks (production)."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from telegram.ext import Application

logger = logging.getLogger(__name__)


def parse_webhook_url(webhook_url: str) -> tuple[str, str]:
    """
    Return (url_path, normalized_webhook_url) for python-telegram-bot.

    url_path is the path component Telegram will POST to (may be multi-segment).
    """
    parsed = urlparse(webhook_url.strip())
    if parsed.scheme not in ("http", "https"):
        raise SystemExit("WEBHOOK_URL must start with http:// or https://")
    if not parsed.netloc:
        raise SystemExit("WEBHOOK_URL must include a host name")
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") or "/"
    url_path = f'{path}webhook' if path.startswith("/") else f"/{path}/webhook"
    normalized = f"{parsed.scheme}://{parsed.netloc}{url_path}"
    return url_path, normalized


async def env_shutdown(telegram_app: Application, env_profile: str):
    if env_profile == 'webhook':
        await telegram_app.shutdown()

    elif env_profile == 'polling':
        await telegram_app.updater.stop()
        await telegram_app.shutdown()

    else:
        raise SystemExit(
            "BOT_TRANSPORT must be 'polling' (default) or 'webhook'. "
            f"Got: {env_profile!r}"
        )


async def env_start(telegram_app: Application, env_profile: str):
    if env_profile == 'webhook':
        webhook_url_raw = os.getenv("WEBHOOK_URL", "").strip()

        if not webhook_url_raw:
            raise SystemExit("WEBHOOK_URL is required when BOT_TRANSPORT=webhook")

        url_path, webhook_url = parse_webhook_url(webhook_url_raw)
        await telegram_app.initialize()
        await telegram_app.bot.set_webhook(webhook_url)

    elif env_profile == "polling":
        logger.info("Starting bot (long polling; set BOT_TRANSPORT=webhook in production)")
        await telegram_app.initialize()
        await telegram_app.updater.start_polling()
        await telegram_app.start()

    else:
        raise SystemExit(
            "BOT_TRANSPORT must be 'polling' (default) or 'webhook'. "
            f"Got: {env_profile!r}"
        )
