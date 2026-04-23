## Airtable

The bot reads the table **`sterilization_request`**. On **`/start`** and **`/myrequests`**, it finds rows where the field **`telegram`** matches the user’s Telegram username, ignoring case and an optional leading `@`.

Add a **`language`** field (single line text or single select) with allowed values **`en`**, **`ru`**, **`ka`** so the form and bot agree. The bot uses the latest row’s **`language`** (see **`AIRTABLE_CREATED_FIELD`**) for message wording when set.

It replies with these fields for each match: **`id`**, **`created_date`**, **`status`**, **`operator`**.

**`/contact`** uses the same matching requests. If **no** request has an **`operator`** assigned, the bot says so and suggests contacting **`@religofsil`**. If at least one request has an **`operator`**, the bot loads the **`operators`** table (matching **`operator_name`** to the request’s **`operator`** value), and shows **id**, **status**, localized operator names (**`operator_name_en`** / **`_ru`** / **`_ka`** by user locale), and Telegram (**`telegram`**). Rows without an assignee are listed as “not assigned yet”; if an assignee has no row or no handle in **`operators`**, the bot says the directory has no Telegram handle for that name.

Users must have a **public Telegram username** set in Telegram settings; otherwise the bot cannot match the form.

## Airtable Automation script

copy [`scripts/airtable_automation_notify.js`](scripts/airtable_automation_notify.js) into the Automation **Run script** action, then add inputs: `recordId`, `notifyBaseUrl`, `webhookSecret`, and optionally **`notifyEvent`** (`new_request` / `operator_assigned` / `status_changed`). Map `recordId` from the trigger’s record id; set **`notifyEvent`** per automation (e.g. `status_changed` for a status-watch automation).

### Notify webhook (new record → Telegram DM)

When a **`sterilization_request`** row is created or updated (e.g. **`telegram`** filled), you can call a small **FastAPI** app that sends the requestor a Telegram message (same summary as `/start`: `id`, `created_date`, `status`, `operator`).

**Telegram rule:** the notify server can only DM users when it can resolve a numeric **`telegram_chat_id`**. **`/start`** and **`/myrequests`** PATCH that id into Airtable for every matching row; the webhook reads it from this record or from another row for the same handle. Without **`telegram_chat_id`** populated (user never matched `/start` or write failed), notify skips sending.

| Variable | Description |
|----------|-------------|
| `NOTIFY_WEBHOOK_SECRET` | Shared secret; required for `POST /notify/airtable`. Send as header `X-Notify-Secret` or JSON field `secret`. |
| `NOTIFY_HOST` / `NOTIFY_PORT` | Bind address for the notify server (defaults `127.0.0.1` and `8080`). |
| `NOTIFY_DEFAULT_LOCALE` | `en`, `ru`, or `ka` only when the webhook body has no **`locale`** and the row’s **`language`** field is empty or unknown. |

On **`/start`** and **`/myrequests`**, **all** `sterilization_request` records that match the user’s handle (same formula as the listing) are updated with their Telegram numeric chat id—not only a single row. If there are **no** matching rows, nothing is written to Airtable.

After a successful notify **`sendMessage`**, the webhook also PATCHes **`telegram_chat_id`** on **every** row for that same Telegram handle where **`telegram_chat_id`** is still empty (so older rows for the same user get filled in one go). The JSON response includes **`telegram_chat_id_rows_patched`** (count of rows in that PATCH batch).

### Notification from Airtable (example)

1. Do steps to Run on Prod
2. Add a new record in the AT base (you can do that manually in `sterilization_request` table). The bot PATCHes the numeric chat id as a string. If PATCH returns **422**, check the field name and type.
3. If everything is correct, the treigger will send a response like that:


   `{"recordId": "<Airtable record id>", "secret": "<NOTIFY_WEBHOOK_SECRET>"}`

   Optional **`event`** (or **`notify_type`**) selects the message template:

   | Value | Use when |
   |-------|----------|
   | `new_request` | (default) New row or generic notify — “New sterilization request…” |
   | `operator_assigned` | **`operator`** was set or changed |
   | `status_changed` | **`status`** was updated |

   Prefer sending `X-Notify-Secret` as a header instead of body `secret` when the automation supports it.

**Operator / status updates (required in Airtable):** The Telegram bot does not see Airtable edits. Add **separate automations** (or one automation per case) with trigger **When a record is updated** in `sterilization_request`, and restrict **watch fields** to **`operator`** and/or **`status`** if your plan supports it. Point each automation at the same `POST /notify/airtable` URL and pass **`event`**: `operator_assigned` or `status_changed` so users get the right wording. Dedup is per `record_id` **and** `event`, so a status change shortly after an operator assignment still delivers both messages.

