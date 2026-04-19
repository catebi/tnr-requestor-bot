# TNR requestor bot

Telegram bot for a TNR sterilisation programme. It helps people who submitted the intake form see their **sterilisation requests** by matching their **public Telegram @username** to the `telegram` field in Airtable.

## Requirements

- Python 3.10 or newer
- A [Telegram bot token](https://t.me/BotFather)
- An [Airtable](https://airtable.com/) base with a table named `sterilization_request` and a personal access token with **`data.records:read`** and **`data.records:write`** for that base (writes are used to store **`telegram_chat_id`** for notify DMs; without write scope, PATCH returns **403 Forbidden**).

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
| `NOTIFY_WEBHOOK_SECRET` | Secret for `POST /notify/airtable` (Airtable automation → notify server) |
| `NOTIFY_HOST` / `NOTIFY_PORT` | Bind for uvicorn notify app (default `127.0.0.1` / `8080`) |

For local development, **long polling** is enough: leave `BOT_TRANSPORT` unset or set it to `polling`. For production behind HTTPS, use **webhooks** and configure your reverse proxy to forward traffic to the process `WEBHOOK_LISTEN` / `PORT`.

### Notify webhook (new record → Telegram DM)

When a **`sterilization_request`** row is created, you can call a small **FastAPI** app that sends the requestor a Telegram message (same summary as `/start`: `id`, `created_date`, `status`, `operator`).

**Telegram rule:** the notify server can only DM users when it can resolve a numeric **`telegram_chat_id`**. **`/start`** and **`/myrequests`** PATCH that id into Airtable for every matching row; the webhook reads it from this record or from another row for the same handle. Without **`telegram_chat_id`** populated (user never matched `/start` or write failed), notify skips sending.

| Variable | Description |
|----------|-------------|
| `NOTIFY_WEBHOOK_SECRET` | Shared secret; required for `POST /notify/airtable`. Send as header `X-Notify-Secret` or JSON field `secret`. |
| `NOTIFY_HOST` / `NOTIFY_PORT` | Bind address for the notify server (defaults `127.0.0.1` and `8080`). |

On **`/start`** and **`/myrequests`**, **all** `sterilization_request` records that match the user’s handle (same formula as the listing) are updated with their Telegram numeric chat id—not only a single row. If there are **no** matching rows, nothing is written to Airtable.

**Airtable base:** add a **Single line text** field **`telegram_chat_id`** on `sterilization_request` (the bot PATCHes the numeric chat id as a string). If PATCH returns **422**, check the field name and type.

**Run the notify server locally (second terminal):**

```bash
# from repo root, venv active, .env loaded
uvicorn tnr_bot.notify_app:app --host "${NOTIFY_HOST:-127.0.0.1}" --port "${NOTIFY_PORT:-8080}"
```

**Expose HTTPS for Airtable (ngrok):**

1. Install [ngrok](https://ngrok.com/) and run: `ngrok http 8080` (or your `NOTIFY_PORT`).
2. Copy the **https://…** forwarding URL (changes each run on free tier).
3. In **Airtable → Automations**, trigger on record created in `sterilization_request`, action **Webhook** or **Run script** that `POST`s JSON, for example:

   `{"recordId": "<Airtable record id>", "secret": "<NOTIFY_WEBHOOK_SECRET>"}`

   to `https://<ngrok-host>/notify/airtable`

   Prefer sending `X-Notify-Secret` as a header instead of body `secret` when the automation supports it.

4. Health check: `GET https://<ngrok-host>/health`

**curl test:**

```bash
curl -sS -X POST "http://127.0.0.1:8080/notify/airtable" \
  -H "Content-Type: application/json" \
  -H "X-Notify-Secret: $NOTIFY_WEBHOOK_SECRET" \
  -d '{"record_id":"recXXXXXXXX"}'
```

**Airtable Automation script:** copy [`scripts/airtable_automation_notify.js`](scripts/airtable_automation_notify.js) into the Automation **Run script** action, then add the three inputs it expects (`recordId`, `notifyBaseUrl`, `webhookSecret`) and map `recordId` from the trigger’s record id.

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
| `tnr_bot/notify_app.py` | FastAPI webhook for Airtable → Telegram (run with uvicorn) |
| `tnr_bot/integrations/airtable_write.py` | Optional PATCH `telegram_chat_id` |
| `tnr_bot/integrations/telegram_api.py` | Outbound `sendMessage` for notify path |

See `PRD.md` for broader product notes (status flows, future features).

## License

This project is licensed under the [MIT License](LICENSE).
