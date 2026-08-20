# Flight price providers — mapping for vacation-is-coming

Amadeus **Self-Service** was decommissioned on **17 July 2026**. The public portal now points to **Enterprise APIs only** (sales/consultant onboarding). For an open-source project shared on LinkedIn, Amadeus is no longer a viable default.

This document maps flight search providers for `src/flights/` (SerpAPI default, Amadeus BYOK optional).

## Summary table

| Provider | Signup | Good for alerts? | Brazil (LDB/PPB → NE) | Cost (typical) | Verdict for vacation-is-coming |
|----------|--------|------------------|------------------------|----------------|---------------------------|
| **Amadeus Self-Service** | Closed | — | Was good | — | **Deprecated** — do not document as default |
| **Amadeus Enterprise** | Sales / contract | Yes | Yes | Enterprise pricing | BYOK for companies only |
| **Duffel** | Self-serve ~1 min, sandbox instant | Yes (search offers) | Check coverage | Sandbox free; production commercial | **Best GDS-style replacement** |
| **SerpAPI (Google Flights)** | Self-serve, API key instant | **Yes** — price monitoring | Yes (Google Flights) | 250 searches/mo free; $25/1k | **Best for “alert only” OSS** |
| **Kiwi Tequila** | Invitation-only B2B since May 2024 | Yes | Yes | Partner deal | **Not for public OSS** |
| **Skyscanner API** | Apply; needs ~100k MAU | Yes | Yes | Commercial | **Not for hobby/OSS** |
| **Travelpayouts + Kiwi** | Affiliate; 50k MAU minimum | Partial | Yes | Revenue share | Too high bar for clones |
| **Scraping (DIY)** | None | Fragile | Possible | Infra + maintenance | **Avoid** for shared product |

## Recommended strategy for vacation-is-coming

### Default for LinkedIn / clones: **SerpAPI (Google Flights)**

**Why**

- Signup in minutes, single API key (`SERPAPI_API_KEY`)
- Fits “monitor prices daily and WhatsApp alert” — no booking needed
- Free tier: **250 searches/month** (enough for small route sets if batched carefully)
- Google Flights covers Brazilian domestic + international well

**Trade-offs**

- Not an airline/GDS API — structured scrape of Google Flights
- Paid beyond free tier
- Round-trip may need two-step flow (`departure_token` for return leg)
- Terms of use via SerpAPI, not direct airline contract

**Env**

```env
FLIGHT_PROVIDER=serpapi
SERPAPI_API_KEY=your_key
```

**Rough API shape (fixed dates)**

```http
GET https://serpapi.com/search?engine=google_flights
  &departure_id=LDB
  &arrival_id=MCZ
  &outbound_date=2027-03-10
  &return_date=2027-03-17
  &currency=BRL
  &api_key=...
```

**Explore mode** (`search_mode: explore` in `travel.yaml`) uses `engine=google_travel_explore` with `month` and `travel_duration`, then optionally `google_flights` on the best dates (`explore.deepen: true`). Horizon ~6 months; roughly doubles API calls when deepening.

**Range mode** (`search_mode: range`) loops `google_flights` once per departure day in the window (max 10 days) per route and ranks the top N cheapest combinations. Duration and stops go in the snapshot; WhatsApp stays a compact summary. Example: 10-day window × 2 routes = 20 calls per run — use `schedule.interval_days` to stay within the free tier.

### Secondary / “real aviation API”: **Duffel**

**Why**

- Self-serve signup at [app.duffel.com](https://app.duffel.com/join)
- Sandbox access token in dashboard (Developers → Access tokens)
- Proper offer-request model; good if you later add booking

**Trade-offs**

- Production access is commercial (like any GDS aggregator)
- Integration is POST offer request → poll/list offers (different from Amadeus GET)
- Verify Brazil domestic coverage for your routes in sandbox before committing

**Env**

```env
FLIGHT_PROVIDER=duffel
DUFFEL_ACCESS_TOKEN=your_test_token
```

### Keep as optional: **Amadeus Enterprise (BYOK)**

Document for users who already have enterprise credentials. Do **not** promise easy signup.

## Providers to avoid as OSS defaults

| Provider | Reason |
|----------|--------|
| Kiwi Tequila | New accounts invitation-only; affiliate path needs 50k MAU |
| Skyscanner API | Application, ~100k MAU, commercial review |
| DIY scraping | Breaks often, legal/ToS risk, bad UX for cron jobs |

## Adapter architecture (target)

Decouple search from WhatsApp/orchestration:

```text
src/flights/
├── __init__.py          # search_all_routes(settings)
├── models.py            # FlightOffer dataclass
├── amadeus.py           # legacy / enterprise BYOK
├── duffel.py
└── serpapi.py           # recommended default

FLIGHT_PROVIDER=serpapi | duffel | amadeus
```

`main.py` and tests depend only on `FlightOffer` + `search_all_routes()`.

## GitHub Secrets (after migration)

| Secret | SerpAPI | Duffel | Amadeus Enterprise |
|--------|---------|--------|---------------------|
| `FLIGHT_PROVIDER` | `serpapi` | `duffel` | `amadeus` |
| `SERPAPI_API_KEY` | yes | — | — |
| `DUFFEL_ACCESS_TOKEN` | — | yes | — |
| `AMADEUS_CLIENT_ID` | — | — | yes |
| `AMADEUS_CLIENT_SECRET` | — | — | yes |
| `AMADEUS_ENV` | — | — | `production` |

WhatsApp secrets unchanged (`CALLMEBOT_*`, etc.).

## Volume check (your current config)

Example **range** setup (10-day window, 2 routes, every 3 days):

10 days × 2 routes × ~10 runs/month ≈ **200 searches/month** (fits free tier).

Example **fixed** setup (2 routes, daily):

2 routes × 30 days ≈ **60 searches/month**.

- SerpAPI free tier (250) is **tight** for daily range mode — use `interval_days`, fewer routes, or a shorter window.
- Options: `schedule.interval_days`, fewer destinations, shorter range window, or merge origins if the provider supports it.

## Status

**Implemented:** `FLIGHT_PROVIDER=serpapi` (default) via `src/flights/serpapi.py`. Amadeus kept as optional BYOK at `src/flights/amadeus.py`. Setup: [`SETUP_SERPAPI.md`](SETUP_SERPAPI.md).

## Suggested doc changes (when implementing)

Done — SerpAPI is the default; see README and `agents/onboarding.md`.

## Sources

- [Amadeus developers portal](https://developers.amadeus.com) — self-service decommission notice
- [Duffel getting started](https://duffel.com/docs/guides/getting-started-with-flights)
- [Kiwi.com B2B / Tequila](https://media.kiwi.com/articles-and-interviews/better-for-business-kiwi-com-takes-a-new-approach-to-partnerships/)
- [SerpAPI Google Flights](https://serpapi.com/google-flights-api)
- [Skyscanner Partners API](https://www.partners.skyscanner.net/product/travel-api)
