# Flight price providers

vacation-is-coming searches prices only (no booking). Default: **SerpAPI → Google Flights**. Amadeus Enterprise is optional BYOK.

| Provider | Role |
|----------|------|
| **SerpAPI (Google Flights)** | Default. Self-serve API key, 250 searches/month free. |
| **Amadeus Enterprise** | Optional, if you already have a contract. Self-Service was shut down in July 2026. |

## SerpAPI (default)

```env
FLIGHT_PROVIDER=serpapi
SERPAPI_API_KEY=your_key
```

Setup: [`SETUP_SERPAPI.md`](SETUP_SERPAPI.md).

- **fixed:** one `google_flights` call per route
- **explore:** `google_travel_explore` for the cheapest week in a month (~6 month horizon), then optional `google_flights` if `explore.deepen: true`
- **range:** one `google_flights` call per departure day per route (window max 10 days)

Free-tier example: 10-day range × 2 routes × ~10 runs/month (`interval_days: 3`) ≈ 200 searches.

## Amadeus Enterprise (optional)

```env
FLIGHT_PROVIDER=amadeus
AMADEUS_CLIENT_ID=...
AMADEUS_CLIENT_SECRET=...
AMADEUS_ENV=production
```

Setup: [`SETUP_AMADEUS.md`](SETUP_AMADEUS.md). Do not use this path unless you already have enterprise credentials.

## GitHub Secrets

| Secret | SerpAPI | Amadeus |
|--------|---------|---------|
| `FLIGHT_PROVIDER` | `serpapi` | `amadeus` |
| `SERPAPI_API_KEY` | yes | — |
| `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET` | — | yes |
| `AMADEUS_ENV` | — | `production` |

WhatsApp secrets are unchanged (`CALLMEBOT_*` or `TWILIO_*`).
