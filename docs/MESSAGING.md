# WhatsApp and SMS front end (Twilio-ready)

Feature phones and WhatsApp reach people the app never will. The same assistant, Hindi understanding and guided conversations run over messages. [`backend/messaging.py`](../backend/messaging.py) is provider-independent: `handle(sender, body)` takes one incoming message and returns the replies. Twilio is only a thin wrapper around it, so you can try everything today without an account.

## In the app: the WhatsApp page
One click from anywhere: the **WhatsApp** tab in the top menu, the 📱 WhatsApp card on Home, or the 📱 WhatsApp link in the assistant box at the bottom right (`#/whatsapp`). It is a phone-shaped chat that talks to the real `/twilio/webhook`, with: tappable options under each reply (instead of typing the number), typing indicator, read ticks and times, a WhatsApp/SMS switch, English/हिंदी quick toggle, a new-chat button (new number, fresh state), **🎙 voice notes** (recorded in the browser, transcribed locally and shown back as "I heard…"), and an **Open this in the app** button when a reply has a page with the result. The standalone version is still at `/messaging/sim`.

## Try it now (no Twilio)
Open **http://localhost:8000/messaging/sim**: a phone-shaped chat that posts the same form fields Twilio does to `/twilio/webhook`. Send `hi`, then a number 1-9, or a sentence in English or Hindi.

```bash
curl -s -X POST "http://localhost:8000/twilio/webhook?format=json" -d "From=whatsapp:+919800000001" -d "Body=hi"
```

## What a person experiences
- `hi` / `नमस्ते` → numbered menu: moneylender check, offer checker, government schemes, papers, harvest planner, fee, emergency, goal, scam help.
- A number starts a tool; the guide asks **one question at a time**; choices are numbered (reply `2`). `CANCEL` stops. Language follows the script they write in (Devanagari → Hindi); `English` / `हिंदी` fixes it.
- Free text works too ("my sahukar charges 5 rupees per hundred a month on 50000 for 10 months").
- **Voice notes (WhatsApp):** transcribed locally, and the transcript is shown back first ("I heard: …") so a mishearing is visible. Needs the Twilio credentials (to download the media).
- WhatsApp replies are fuller (bold headline, bullets, key figures, optional link); SMS replies are one short message.

## Connect Twilio (when you are ready)
1. Twilio console → Messaging → *Try it out → WhatsApp sandbox* (or buy an SMS number).
2. Expose the backend publicly, for example `ngrok http 8000`, and set `PUBLIC_BASE_URL=https://<id>.ngrok.app`.
3. In the sandbox / number settings set **"When a message comes in"** to `POST https://<id>.ngrok.app/twilio/webhook` (status callback, optional: `/twilio/status`).
4. Set environment variables (see `.env.example`) and restart: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `TWILIO_SMS_FROM`, and **`JARVIS_TWILIO_VALIDATE=1`** so requests without a valid `X-Twilio-Signature` get HTTP 403.
5. `GET /messaging/status` shows which settings are present (never the secrets).

Replies are returned as TwiML (`<Response><Message>…`), so no REST call is needed for conversations. `messaging.send(to, body, channel)` is ready for proactive messages (reminders) via Twilio's REST API.

## Safety and privacy
- Message bodies are not stored or logged. State is language + the open question, in memory, keyed by a one-way hash of the number (expires after 6 hours).
- Stock and portfolio questions are not offered (no portfolio belongs to a phone number); the goal chart uses a labelled sample portfolio.
- 30 messages a minute per sender; bodies capped at 1000 characters.
- Every first reply carries "general information, not financial advice; never share your OTP or PIN".
- Hindi SMS is sent as Unicode (about 70 characters per segment), so replies are kept short and cost more; WhatsApp has no such limit.
- Twilio handles STOP/START opt-out for SMS itself.

## Tests
`tests/test_messaging.py` (13): menu, numbered choices end to end, calculator parity, Hindi detection, SMS vs WhatsApp length, no portfolio answers, cancel, phone-number hashing, rate limit, TwiML escaping, Twilio signature algorithm, message splitting, outbound REST call shape.
