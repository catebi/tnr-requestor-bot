/**
 * Airtable Automation — "Run script" action
 *
 * Trigger: When a record is created (or updated) in `sterilization_request`.
 *
 * Before running:
 * 1. In the Automation editor, add this script and define inputs (see `input.config()` below).
 * 2. Map **recordId** from the trigger: choose "Record ID" / Airtable record id (starts with `rec`).
 * 3. Set **notifyBaseUrl** to your public base URL only, e.g. `https://abcd.ngrok-free.app`
 *    (no trailing slash; update when ngrok restarts on the free tier).
 * 4. Set **webhookSecret** to the same value as `NOTIFY_WEBHOOK_SECRET` on your server.
 *    Prefer Airtable **Secrets** (Workspace settings) or a hidden input if your plan supports it.
 *
 * The server expects:
 *   POST {notifyBaseUrl}/notify/airtable
 *   Header: X-Notify-Secret: <webhookSecret>
 *   JSON body: { "recordId": "<rec...>", "event": "<optional>" }
 *   event: omit or "new_request" | "operator_assigned" | "status_changed"
 *
 * Requires: Automation "Run script" with `fetch` available (check your Airtable plan).
 */

async function fetch_error(error_message){
  const error_url = `${notifyBaseUrl}/log_error`;
  const body = {'automation_name': String(notifyEvent).trim(),
  'error_message': error_message};

  const response = await fetch(error_url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify(body),
  });

  const text = await response.text();

  if (!response.ok) {
    throw new Error(`Log Error request failed: HTTP ${response.status} — ${text}`);
  }

  console.log(`Log Error OK: HTTP ${response.status}`);
  console.log(text.length > 800 ? text.slice(0, 800) + "…" : text)
}

const { recordId, notifyBaseUrl, notifyEvent } = input.config();
const webhookSecret = input.secret("webhookSecret")

if (!notifyBaseUrl || String(notifyBaseUrl).trim() === "") {
  throw new Error("Set automation input `notifyBaseUrl` (e.g. your ngrok https URL).");
}
if (!webhookSecret || String(webhookSecret).trim() === "") {
  await fetch_error('Set automation input `webhookSecret` to match NOTIFY_WEBHOOK_SECRET.');
}
if (!recordId || String(recordId).trim() === "") {
  await fetch_error('Automation input `recordId` is missing. Map it from the trigger record.')
}


// const base = String(notifyBaseUrl).trim().replace(/\/+$/, "");
const url = `${notifyBaseUrl}/notify/airtable`;

const body = { recordId: String(recordId).trim() };
if (notifyEvent != null && String(notifyEvent).trim() !== "") {
  body.event = String(notifyEvent).trim();
}

const response = await fetch(url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Notify-Secret": String(webhookSecret).trim(),
  },
  body: JSON.stringify(body),
});

const text = await response.text();

if (!response.ok) {
  await fetch_error(`Notify webhook failed: HTTP ${response.status} — ${text}`);
}

console.log(`Notify OK: HTTP ${response.status}`);
console.log(text.length > 800 ? text.slice(0, 800) + "…" : text);
