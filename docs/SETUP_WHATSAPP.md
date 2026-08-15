# Configure WhatsApp with CallMeBot

Step-by-step guide to receive price alerts on WhatsApp.

## 1. Activate CallMeBot on your phone

1. Save the number **+34 621 062 163** in your contacts (e.g. `CallMeBot`).
2. In WhatsApp, send exactly:
   ```text
   I allow callmebot to send me messages
   ```
3. Within a few minutes the bot replies with something like:
   ```text
   API Activated for your phone number. Your APIKEY is 123123
   ```
4. Save the **APIKEY**.

> If the key does not arrive within ~2 minutes, try again after 24 hours.

## 2. Fill in your local `config/.env`

```bash
cp config/.env.example config/.env
```

Edit `config/.env`:

```env
WHATSAPP_PROVIDER=callmebot
CALLMEBOT_PHONE=15551234567
CALLMEBOT_APIKEY=your_key_here
```

- Phone with country code, **no spaces** (e.g. Brazil: `5543999999999`, US: `15551234567`)
- Must be **the same number** that activated CallMeBot (the one that received the APIKEY)
- If unsure, send `Recover APIKey` to the CallMeBot contact on WhatsApp
- Amadeus credentials can stay empty for the WhatsApp-only test

## 3. Test sending

```bash
python -m src --test-whatsapp
```

If configured correctly, you receive:

```text
✅ vacation-is-coming — WhatsApp test OK
If you received this, WhatsApp alerts are configured.
```

## 4. GitHub Secrets (daily automation)

In the repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|--------|--------|
| `FLIGHT_PROVIDER` | `serpapi` |
| `SERPAPI_API_KEY` | SerpAPI key — see [`SETUP_SERPAPI.md`](SETUP_SERPAPI.md) |
| `WHATSAPP_PROVIDER` | `callmebot` |
| `CALLMEBOT_PHONE` | your phone with country code |
| `CALLMEBOT_APIKEY` | key from the bot |

Then: **Actions → Check flight prices and notify on WhatsApp → Run workflow**.

## Common issues

| Symptom | What to do |
|---------|------------|
| No APIKEY received | Resend the activation phrase after 24h |
| Apikey error | Copy only the digits, no spaces |
| Message never arrives | Phone/apikey mismatch: re-check Secrets match the activated WhatsApp number; send `Recover APIKey` to CallMeBot |
| Long alert with many routes | Split into a few parts; CallMeBot free tier: **16 messages / 4 hours** |
| Want to message someone else | Free CallMeBot only sends to the activated number; use Twilio |
