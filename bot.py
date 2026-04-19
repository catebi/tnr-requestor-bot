"""
TNR sterilization bot: /start matches Telegram username to Airtable `telegram` field.

Run:  python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
       cp .env.example .env   # fill in secrets
       python bot.py

Transport:
  - Local: BOT_TRANSPORT=polling (default) — long polling, no public URL needed.
  - Production: BOT_TRANSPORT=webhook — set WEBHOOK_URL to the public HTTPS URL Telegram
    should call; bind with WEBHOOK_LISTEN / PORT (often behind a reverse proxy).
"""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import MessageLimit
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

AIRTABLE_API = "https://api.airtable.com/v0"
AIRTABLE_TABLE = "sterilization_request"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

if ENVIRONMENT == "dev":
    AIRTABLE_PAT = os.getenv("AIRTABLE_PAT_DEV")
    AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID_DEV")
else:
    AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
    AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

def normalize_handle(raw: str) -> str:
    """Match form entries with or without leading @."""
    s = raw.strip()
    if s.startswith("@"):
        s = s[1:]
    return s.lower()


def escape_airtable_formula_string(s: str) -> str:
    """Escape single quotes for Airtable formula string literals."""
    return s.replace("'", "''")


def filter_by_telegram_formula(normalized_username: str) -> str:
    """
    Records where `telegram` equals the user's handle, ignoring case and a single leading @.
    """
    esc = escape_airtable_formula_string(normalized_username)
    return (
        "AND("
        "{telegram} != '', "
        "LOWER(TRIM(SUBSTITUTE({telegram}, '@', ''))) = "
        f"'{esc}'"
        ")"
    )


def format_field(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.append(item.get("name") or item.get("email") or str(item))
            else:
                parts.append(str(item))
        return ", ".join(parts) if parts else "—"
    if isinstance(value, dict):
        return value.get("name") or value.get("email") or str(value)
    return str(value)


def build_summary_text(records: list[dict[str, Any]], compact: bool = False) -> str:
    blocks: list[str] = []
    for i, rec in enumerate(records, start=1):
        fields = rec.get("fields") or {}
        rec_id = fields.get("id")
        if rec_id is None:
            rec_id = rec.get("id", "—")
        if compact:
            blocks.append(
                f"{i}. id={format_field(rec_id)} | created_date={format_field(fields.get('created_date'))} | "
                f"status={format_field(fields.get('status'))} | operator={format_field(fields.get('operator'))}"
            )
        else:
            line = (
                f"{i}. id: {format_field(rec_id)}\n"
                f"   created_date: {format_field(fields.get('created_date'))}\n"
                f"   status: {format_field(fields.get('status'))}\n"
                f"   operator: {format_field(fields.get('operator'))}"
            )
            blocks.append(line)
    sep = "\n" if compact else "\n\n"
    return sep.join(blocks)


async def fetch_matching_records(normalized_username: str) -> list[dict[str, Any]]:
    base_id = AIRTABLE_BASE_ID
    token = AIRTABLE_PAT
    formula = filter_by_telegram_formula(normalized_username)
    headers = {"Authorization": f"Bearer {token}"}
    out: list[dict[str, Any]] = []
    offset: str | None = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            params: dict[str, str | int] = {
                "filterByFormula": formula,
                "pageSize": 100,
            }
            if offset:
                params["offset"] = offset

            url = f"{AIRTABLE_API}/{base_id}/{AIRTABLE_TABLE}"
            r = await client.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
            out.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break

    return out


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

    # Telegram hard limit; split only if still too long.
    if len(text) <= MessageLimit.MAX_TEXT_LENGTH:
        await update.message.reply_text(text)
        return

    chunk_size = MessageLimit.MAX_TEXT_LENGTH
    for start in range(0, len(text), chunk_size):
        part = text[start : start + chunk_size]
        await update.message.reply_text(part)


def _parse_webhook_url(webhook_url: str) -> tuple[str, str]:
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
    # PTB accepts path with or without leading slash; Updater normalizes to start with /
    url_path = path if path.startswith("/") else f"/{path}"
    # Rebuild a canonical URL without stray fragments/query for setWebhook
    normalized = f"{parsed.scheme}://{parsed.netloc}{url_path}"
    return url_path, normalized


def _run_application(app: Application, transport: str) -> None:
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

        url_path, webhook_url = _parse_webhook_url(webhook_url_raw)
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


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        raise SystemExit(
            "Airtable credentials missing: set AIRTABLE_PAT / AIRTABLE_BASE_ID "
            "(or AIRTABLE_*_DEV when ENVIRONMENT=dev)"
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_cmd))

    transport = os.getenv("BOT_TRANSPORT", "polling")
    _run_application(app, transport)


if __name__ == "__main__":
    main()
