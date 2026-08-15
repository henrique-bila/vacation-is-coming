# Configure SerpAPI (Google Flights)

vacation-is-coming uses [SerpAPI](https://serpapi.com/google-flights-api) to search Google Flights and build WhatsApp price alerts. No airline contract required.

## 1. Create an account

1. Sign up at [serpapi.com](https://serpapi.com/users/sign_up).
2. Open the [Dashboard](https://serpapi.com/manage-api-key) and copy your **API Key**.

## 2. GitHub Secrets (remote execution)

In the repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|--------|--------|
| `FLIGHT_PROVIDER` | `serpapi` |
| `SERPAPI_API_KEY` | your API key |
| `WHATSAPP_PROVIDER` | `callmebot` |
| `CALLMEBOT_PHONE` | phone with country code |
| `CALLMEBOT_APIKEY` | CallMeBot key |

Then: **Actions → Check flight prices and notify on WhatsApp → Run workflow**.

## 3. Usage limits

- **Free plan:** 250 searches/month
- Cost **per search run** depends on `search_mode`:
  - **`fixed`:** 1 SerpAPI call × each route
  - **`explore`:** ~1–2 calls × each route (`deepen: true` adds a second call)
  - **`range`:** (departure days in window) × each route — e.g. 10 days × 2 routes = **20 calls/run**
- Combine with `schedule.interval_days` to reduce runs (cron stays daily; script skips until elapsed)
- Example: range 10 days × 2 routes × ~10 runs/month (every 3 days) ≈ **200 searches/month**

Pricing: [serpapi.com/pricing](https://serpapi.com/pricing)

## 4. Verify (optional, local)

Only if you want to test on your machine:

```bash
cp config/.env.example config/.env
# fill SERPAPI_API_KEY
python -m src --dry-run
```

For production use, prefer **GitHub Actions** with Secrets (no local `.env` required).

## Troubleshooting

| Symptom | What to do |
|---------|------------|
| `Required environment variable missing: SERPAPI_API_KEY` | Add the Secret or `config/.env` |
| SerpAPI quota exceeded | Reduce routes, run every other day, or upgrade plan |
| No offers for a route | Check IATA codes and dates in `config/travel.yaml` |

See also: [`docs/FLIGHT_PROVIDERS.md`](FLIGHT_PROVIDERS.md)
