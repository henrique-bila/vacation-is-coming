# vacation-is-coming

Searches Google Flights (via SerpAPI) and sends a WhatsApp summary. Runs on GitHub Actions. Works with any AI coding agent (Cursor, Claude, Codex, GPT, and others).

Guia em português (do zero ao WhatsApp): [`docs/GUIA_USUARIO.md`](docs/GUIA_USUARIO.md)

## How it works

1. You set routes, **date mode** (`fixed`, `explore`, or `range`), and a schedule in `config/travel.yaml` (or ask an AI agent).
2. GitHub Actions searches Google Flights (skips days when `interval_days` has not elapsed).
3. WhatsApp gets a short summary vs the last run. Airline, stops, duration, and range top-N days go in `config/snapshots/`.
4. Optional: only send if a price is under `PRICE_ALERT_MAX`.

```text
config/travel.yaml  →  SerpAPI (Google Flights)  →  WhatsApp
                     ↑
              GitHub Actions (daily cron)
```

## Quick start

Fork the repo (so Actions and Secrets are yours), then:

```bash
git clone https://github.com/YOUR_USER/vacation-is-coming.git
cd vacation-is-coming

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r config/requirements.txt

cp config/.env.example config/.env
```

Edit `config/.env` (keys) and `config/travel.yaml` (routes + schedule). YAML has no secrets.

Searches stay off until you set `configured: true`. Until then, local runs and the daily Action skip without failing.

```bash
python -m src --test-whatsapp   # WhatsApp only
python -m src --dry-run         # search, do not send
python -m src                   # search and send
python -m src --force           # ignore interval_days
python -m src --sync-schedule   # travel.yaml schedule → Actions UTC cron
```

## Date modes

| Mode | When | Config |
|------|------|--------|
| `fixed` | Exact dates | `departure_date` / `return_date` on each route |
| `explore` | Cheapest week in a month (SerpAPI) | `explore.month`, `travel_duration`, `deepen` |
| `range` | Cheapest days in a window (SerpAPI, max 10 days) | `range.departure_window_*`, `trip_duration_days`, `top_combinations` |

```yaml
search_mode: range
range:
  departure_window_start: "2027-02-05"
  departure_window_end: "2027-02-14"
  trip_duration_days: 7
  top_combinations: 3
schedule:
  interval_days: 3   # optional — fewer SerpAPI calls
```

Explore’s calendar API looks ~6 months ahead. Range costs one search per departure day per route. Details: [`docs/FLIGHT_PROVIDERS.md`](docs/FLIGHT_PROVIDERS.md).

## Use with an AI agent

1. Open the repo in Cursor, Claude Code, Codex, GPT, or similar.
2. Point the agent at [`AGENTS.md`](AGENTS.md).
3. Say what you want, for example:
   - “Monitor daily at 8am: JFK to Miami, March 10–17 2027”
   - “Range mode: cheapest 3 days between Feb 5–14, 7-day trip”
   - “Explore mode for Salvador in February — cheapest week”
   - “Only alert if the price is under $350”
   - “Search every 3 days to save SerpAPI quota”
   - “Publish to git”

The agent updates `config/preferences.md` + `config/travel.yaml`. Push to **your fork** so Actions picks it up (`agents/git.md`). Never commit `config/.env`.

## Credentials

| Need | Setup |
|------|--------|
| Flight search | [`docs/SETUP_SERPAPI.md`](docs/SETUP_SERPAPI.md) (default). Amadeus enterprise: [`docs/SETUP_AMADEUS.md`](docs/SETUP_AMADEUS.md) |
| WhatsApp | [`docs/SETUP_WHATSAPP.md`](docs/SETUP_WHATSAPP.md) (CallMeBot or Twilio) |

Put keys in `config/.env` locally and in **GitHub Secrets** for Actions.

| Secret | When |
|--------|------|
| `SERPAPI_API_KEY` | SerpAPI (default) |
| `FLIGHT_PROVIDER` | optional: `serpapi` or `amadeus` |
| `WHATSAPP_PROVIDER` | optional: `callmebot` or `twilio` |
| `CALLMEBOT_PHONE` / `CALLMEBOT_APIKEY` | CallMeBot |
| `TWILIO_*` | Twilio |
| `AMADEUS_*` | Amadeus enterprise |
| `PRICE_ALERT_MAX` | optional cap |

## GitHub Actions

[`.github/workflows/check-prices.yml`](.github/workflows/check-prices.yml) runs daily (cron synced with `--sync-schedule`). Manual **Run workflow** uses `--force`.

If `configured: false`, the job exits 0 (no API calls). After a real search it commits a snapshot under `config/snapshots/`.

After a DST change, run `--sync-schedule` and push the workflow.

## Example messages

**WhatsApp** (all date modes):

```text
Flight price alert - Example trip
Mode: fixed dates

Vs last: 1 down, 0 up, 0 flat
Biggest drop: JFK -> MIA -30

Top drops:
• JFK -> MIA: 10-Mar-17-Mar · USD 420 (-30 vs last, 7d min 400)

Cheapest today:
• JFK -> MIA: 10-Mar-17-Mar · USD 420 (-30 vs last, 7d min 400)

Full history: config/snapshots/
```

**Snapshot** (airline, stops, duration, range top-N):

```text
Flight price alert - Example trip
Mode: fixed dates

*JFK -> MIA* (2027-03-10 -> 2027-03-17)
1. USD 420.00 (-30 vs last, 7d min 400) — LATAM (nonstop, 3h10m)
```
