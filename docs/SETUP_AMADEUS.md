# Configure Amadeus (flight prices — enterprise BYOK)

> **Note:** Amadeus Self-Service was decommissioned in July 2026. New users should use **SerpAPI** — see [`SETUP_SERPAPI.md`](SETUP_SERPAPI.md). This guide is for existing enterprise Amadeus customers only (`FLIGHT_PROVIDER=amadeus`).

vacation-is-coming can use the [Amadeus Flight Offers Search API](https://developers.amadeus.com) when you bring your own enterprise credentials.

## 1. Create an account and app

1. Sign up at [developers.amadeus.com](https://developers.amadeus.com).
2. Create a **Self-Service** app.
3. Copy the **API Key** (`AMADEUS_CLIENT_ID`) and **API Secret** (`AMADEUS_CLIENT_SECRET`).

## 2. Local `config/.env`

```env
AMADEUS_CLIENT_ID=your_key
AMADEUS_CLIENT_SECRET=your_secret
AMADEUS_ENV=test
```

- `test` — sandbox data (not real market prices)
- `production` — real prices (enable production access in the Amadeus dashboard)

## 3. GitHub Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `AMADEUS_CLIENT_ID` | yes | API Key |
| `AMADEUS_CLIENT_SECRET` | yes | API Secret |
| `AMADEUS_ENV` | no | `test` or `production` |

## 4. Verify locally

```bash
python -m src --dry-run
```

This searches routes from `config/travel.yaml` and prints the WhatsApp message
without sending it.
