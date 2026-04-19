# TNR requestor bot

Telegram bot for a TNR sterilisation programme. It helps people who submitted the intake form see their **sterilisation requests** by matching their **public Telegram @username** to the `telegram` field in Airtable.

## Requirements

- Python 3.10 or newer
- A [Telegram bot token](https://t.me/BotFather)
- An [Airtable](https://airtable.com/) base with a table named `sterilization_request` and a personal access token that can read that base

## Setup

```bash
cd tnr-requestor-bot
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and Airtable credentials
```

## Run

From the repository root (with the virtual environment activated):

```bash
python bot.py
```

Or:

```bash
python -m tnr_bot
```

## Environment variables

Copy `.env.example` to `.env` and set the values you need.

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather (required) |
| `ENVIRONMENT` | `dev` (default) uses `AIRTABLE_PAT_DEV` / `AIRTABLE_BASE_ID_DEV`; otherwise uses `AIRTABLE_PAT` / `AIRTABLE_BASE_ID` |
| `AIRTABLE_PAT` / `AIRTABLE_BASE_ID` | Production Airtable token and base id |
| `AIRTABLE_PAT_DEV` / `AIRTABLE_BASE_ID_DEV` | Optional separate base for local development |
| `BOT_TRANSPORT` | `polling` (default, local) or `webhook` (production) |
| `WEBHOOK_URL` | Full public HTTPS URL Telegram should call (required if `BOT_TRANSPORT=webhook`) |
| `WEBHOOK_LISTEN` | Bind address (default `0.0.0.0`) |
| `PORT` | Listen port for the webhook server (default `8080`) |
| `WEBHOOK_SECRET` | Optional Telegram webhook secret token |

For local development, **long polling** is enough: leave `BOT_TRANSPORT` unset or set it to `polling`. For production behind HTTPS, use **webhooks** and configure your reverse proxy to forward traffic to the process `WEBHOOK_LISTEN` / `PORT`.

## Airtable

The bot reads the table **`sterilization_request`**. On `/start`, it finds rows where the field **`telegram`** matches the user’s Telegram username, ignoring case and an optional leading `@`.

It replies with these fields for each match: **`id`**, **`created_date`**, **`status`**, **`operator`**.

Users must have a **public Telegram username** set in Telegram settings; otherwise the bot cannot match the form.

## Project layout

The code lives in the **`tnr_bot`** package:

| Area | Role |
|------|------|
| `tnr_bot/config.py` | Environment and credentials |
| `tnr_bot/integrations/airtable.py` | Airtable API and query formulas |
| `tnr_bot/handlers/` | Command handlers; register new ones in `handlers/register.py` |
| `tnr_bot/utils/` | Formatting and small helpers |
| `tnr_bot/runtime/transport.py` | Polling vs webhook startup |
| `tnr_bot/app.py` | Application factory and `main()` |

See `PRD.md` for broader product notes (status flows, future features).

## License

This project is licensed under the [MIT License](LICENSE).
