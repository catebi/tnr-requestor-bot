/**
 * Airtable Automation — "Run script" action
 *
 * Trigger: When a record is created (or updated) in `sterilization_request`.
 *
 * Before running:
 * 1. In the Automation editor, add this script and define **three inputs** (see `input.config()` below).
 * 2. Map **recordId** from the trigger: choose "Record ID" / Airtable record id (starts with `rec`).
 * 3. Set **notifyBaseUrl** to your public base URL only, e.g. `https://abcd.ngrok-free.app`
 *    (no trailing slash; update when ngrok restarts on the free tier).
 * 4. Set **webhookSecret** to the same value as `NOTIFY_WEBHOOK_SECRET` on your server.
 *    Prefer Airtable **Secrets** (Workspace settings) or a hidden input if your plan supports it.
 *
 * The server expects:
 *   POST {notifyBaseUrl}/notify/airtable
 *   Header: X-Notify-Secret: <webhookSecret>
 *   JSON body: { "recordId": "<rec...>" }
 *
 * Requires: Automation "Run script" with `fetch` available (check your Airtable plan).
 */

const { recordId, notifyBaseUrl, webhookSecret } = input.config();

if (!recordId || String(recordId).trim() === "") {
  throw new Error("Automation input `recordId` is missing. Map it from the trigger record.");
}

if (!notifyBaseUrl || String(notifyBaseUrl).trim() === "") {
  throw new Error("Set automation input `notifyBaseUrl` (e.g. your ngrok https URL).");
}

if (!webhookSecret || String(webhookSecret).trim() === "") {
  throw new Error("Set automation input `webhookSecret` to match NOTIFY_WEBHOOK_SECRET.");
}

const base = String(notifyBaseUrl).trim().replace(/\/+$/, "");
const url = `${base}/notify/airtable`;

const response = await fetch(url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Notify-Secret": String(webhookSecret).trim(),
  },
  body: JSON.stringify({ recordId: String(recordId).trim() }),
});

const text = await response.text();

if (!response.ok) {
  throw new Error(`Notify webhook failed: HTTP ${response.status} — ${text}`);
}

console.log(`Notify OK: HTTP ${response.status}`);
console.log(text.length > 800 ? text.slice(0, 800) + "…" : text);
