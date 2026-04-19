"""Run the bot with long polling (dev) or webhooks (production)."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from telegram import Update
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
    url_path = path if path.startswith("/") else f"/{path}"
    normalized = f"{parsed.scheme}://{parsed.netloc}{url_path}"
    return url_path, normalized


def run_application(app: Application, transport: str) -> None:
    transport = transport.strip().lower()
    allowed = Update.ALL_TYPES

    if transport in ("", "polling", "poll", "long_polling", "long-polling"):
        logger.info("Starting bot (long polling; set BOT_TRANSPORT=webhook in production)")
        app.run_polling(allowed_updates=allowed)
        return

    if transport in ("webhook", "hooks"):
        webhook_url_raw = os.getenv("WEBHOOK_URL", "").strip()
        if not webhook_url_raw:
            raise SystemExit("WEBHOOK_URL is required when BOT_TRANSPORT=webhook")

        url_path, webhook_url = parse_webhook_url(webhook_url_raw)
        listen = os.getenv("WEBHOOK_LISTEN", "0.0.0.0").strip() or "0.0.0.0"
        port_str = os.getenv("PORT", "8080").strip() or "8080"
        try:
            port = int(port_str)
        except ValueError as exc:
            raise SystemExit("PORT must be an integer") from exc

        secret_token = os.getenv("WEBHOOK_SECRET")
        if secret_token is not None:
            secret_token = secret_token.strip() or None

        logger.info(
            "Starting bot (webhook): listen=%s port=%s path=%s public=%s",
            listen,
            port,
            url_path,
            webhook_url,
        )
        app.run_webhook(
            listen=listen,
            port=port,
            url_path=url_path,
            webhook_url=webhook_url,
            allowed_updates=allowed,
            secret_token=secret_token,
        )
        return

    raise SystemExit(
        "BOT_TRANSPORT must be 'polling' (default) or 'webhook'. "
        f"Got: {transport!r}"
    )
