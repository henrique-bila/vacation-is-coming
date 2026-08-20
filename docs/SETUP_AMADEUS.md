# Configure Amadeus (enterprise BYOK)

Amadeus **Self-Service** was shut down in July 2026. New users should use **SerpAPI** — [`SETUP_SERPAPI.md`](SETUP_SERPAPI.md).

This path is only for people who **already** have Amadeus Enterprise credentials (`FLIGHT_PROVIDER=amadeus`).

## Local `config/.env`

```env
FLIGHT_PROVIDER=amadeus
AMADEUS_CLIENT_ID=your_key
AMADEUS_CLIENT_SECRET=your_secret
AMADEUS_ENV=production
```

## GitHub Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `FLIGHT_PROVIDER` | yes | `amadeus` |
| `AMADEUS_CLIENT_ID` | yes | Enterprise API key |
| `AMADEUS_CLIENT_SECRET` | yes | Enterprise API secret |
| `AMADEUS_ENV` | no | `production` (or `test` if your contract includes a sandbox) |

## Verify locally

```bash
python -m src --dry-run
```

This searches routes from `config/travel.yaml` and prints the alert without sending WhatsApp.
