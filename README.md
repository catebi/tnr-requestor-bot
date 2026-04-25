# TNR requestor bot

Telegram bot for a TNR sterilization program. It helps people who submitted the intake form see their **sterilization requests** by matching their **public Telegram @username** to the `telegram` field in Airtable.

User-facing messages use **English**, **Russian**, or **Georgian** (`en`, `ru`, `ka`). When the user has matching (by name) **`sterilization_request`** rows, the bot reads **`language`** from the **latest** row (by **`created_date`**, configurable) and prefers that over the Telegram app language; otherwise it falls back to Telegram, then English. 

**`/language`** updates **`language`** on every matching row. The notify webhook picks language in this order: JSON **`locale`** → Airtable **`language`** on the notified row → **`NOTIFY_DEFAULT_LOCALE`**.

**`/status` in messages:** single-select values are translated for display using [`tnr_bot/locale/field_display.py`](tnr_bot/locale/field_display.py); map keys must match the **exact** strings in Airtable (see PRD §4.1). 

**`/operator`** display names come from fixed fields on **`operators`**: **`operator_name_en`**, **`operator_name_ru`**, **`operator_name_ka`**, with fallback to **`operator_name`** when a localized cell is empty. Matching and formulas still use stored **`sterilization_request.operator`** and **`operators.telegram`** values unchanged.

## Requirements

- Python 3.10 or newer
- A [Telegram bot token](https://t.me/BotFather)
- An [Airtable](https://airtable.com/) base with a table named `sterilization_request` and a personal access token with **`data.records:read`** and **`data.records:write`** for that base (writes are used to store **`telegram_chat_id`** for notify DMs; without write scope, PATCH returns **403 Forbidden**).

#### For prod testing:

- ngrok and credentials from [ngrok](https://dashboard.ngrok.com/get-started/setup/linux) connection (create an account): `WEBHOOK_SECRET` from ngrok config codeline, `WEBHOOK_URL` under the 'ngrok http' codeline


## Setup

```bash
cd tnr-requestor-bot
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env # copypaste if .env not exists
# Edit .env with your TELEGRAM_BOT_TOKEN and Airtable credentials
```

## Environment variables

Copy `.env.example` to `.env` and set the values you need.

| Variable                                    | Description                                                                                                               |
|---------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `APP_NAME`                        | Application name for logging messages                                                                                     |
| `TELEGRAM_BOT_TOKEN`                        | Bot token from BotFather (required)                                                                                       |
| `LOGS_CHAT_ID`                              | ID of the chat where the bot should send warnings and errors to                                                           |
| `DEVELOPERS`                                | @usernames of the developers (comma separated) so the bot can ping them logging the errors                                |
| `ENVIRONMENT`                               | `dev` (default) uses `AIRTABLE_PAT_DEV` / `AIRTABLE_BASE_ID_DEV`; otherwise uses `AIRTABLE_PAT` / `AIRTABLE_BASE_ID`      |
| `AIRTABLE_PAT` / `AIRTABLE_BASE_ID`         | Production Airtable token and base id                                                                                     |
| `AIRTABLE_PAT_DEV` / `AIRTABLE_BASE_ID_DEV` | Optional separate base for local development                                                                              |
| `BOT_TRANSPORT`                             | `polling` (default, local) or `webhook` (production)                                                                      |
| `WEBHOOK_URL`                               | Full public HTTPS URL Telegram should call (required if `BOT_TRANSPORT=webhook`)                                          |
| `WEBHOOK_SECRET`                            | Optional Telegram webhook secret token                                                                                    |
| `NOTIFY_WEBHOOK_SECRET`                     | Secret for `POST /notify/airtable` (Airtable automation → notify server)                                                  |
| `NOTIFY_HOST` / `NOTIFY_PORT`               | Bind for uvicorn notify app (default `127.0.0.1` / `8080`)                                                                |
| `NOTIFY_DEFAULT_LOCALE`                     | Default language for notify DMs when JSON `locale` and Airtable `language` are absent: `en`, `ru`, or `ka` (default `en`) |
| `AIRTABLE_LANGUAGE_FIELD`                   | Field on **`sterilization_request`** for preferred locale (default `language`; values `en` / `ru` / `ka`)                 |
| `AIRTABLE_CREATED_FIELD`                    | Date/time field used to find the “latest” request (default `created_date`)                                                |

## Run

#### Local development (only Telegram Application testing):

Leave `BOT_TRANSPORT` unset or set it to `polling` and run:

```bash
uvicorn tnr_bot.app:app --host ${NOTIFY_HOST:127.0.0.1} --port ${NOTIFY_PORT:8080}
```

#### Prod development (with Telegram and Airtable Webhook):

1. Install [ngrok](https://ngrok.com/)
2. Configure `WEBHOOK_URL` and `WEBHOOK_SECRET` in .env from [ngrok setup](https://dashboard.ngrok.com/get-started/setup/linux)
3. Open Airtable Base, then → Automations, find tg record script automations
4. Insert `WEBHOOK_URL` in `notifyBaseUrl` field
3. Run in first terminal:
```bash
uvicorn tnr_bot.app:app --host ${NOTIFY_HOST:127.0.0.1} --port ${NOTIFY_PORT:8080}
```
4. Run in second terminal:
```bash
ngrok http ${NOTIFY_PORT:8080}
```


Health check: `GET https://<ngrok-host>/health`

curl test:

```bash
curl -sS -X POST "http://127.0.0.1:8080/notify/airtable" \
  -H "Content-Type: application/json" \
  -H "X-Notify-Secret: $NOTIFY_WEBHOOK_SECRET" \
  -d '{"record_id":"recXXXXXXXX","event":"status_changed"}'
```


## Project layout

TBA

## License

This project is licensed under the [MIT License](LICENSE).
