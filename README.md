# vacation-is-coming

**Track flight deals for your next trip — vacation is coming.**

Open-source automation that searches flight prices (SerpAPI / Google Flights) and sends a WhatsApp summary (CallMeBot or Twilio). Runs on **GitHub Actions** (daily cron; optional `interval_days` to skip API calls). Works with **any AI coding agent** — Cursor, Claude, Codex, GPT, and others.

## Stack

| Layer | Tool |
|-------|------|
| Runtime | Python 3.12 |
| Flight search | [SerpAPI](https://serpapi.com) → Google Flights (default); Amadeus BYOK optional |
| WhatsApp | [CallMeBot](https://www.callmebot.com/blog/free-api-whatsapp-messages/) (default) or Twilio |
| Automation | GitHub Actions (cron + manual run with `--force`) |
| Config | YAML (`config/travel.yaml`) + GitHub Secrets |
| AI setup | Any agent reading `AGENTS.md` + `agents/` playbooks |

## How it works

1. You define routes, **date mode** (`fixed`, `explore`, or `range`), and a schedule in `config/travel.yaml` (or ask an AI agent to do it).
2. GitHub Actions searches Google Flights via SerpAPI for the best offers (skips days when `interval_days` has not elapsed).
3. It builds a **WhatsApp summary** (format depends on mode — range shows top N days with stops and duration).
4. It sends the message — or only when a price is under an optional `PRICE_ALERT_MAX`.
5. It saves a **full Markdown snapshot** in `config/snapshots/` with a comparison table and top offers per route (committed by Actions).

```text
config/travel.yaml  →  SerpAPI (Google Flights)  →  WhatsApp alert
                     ↑
              GitHub Actions (daily cron; may skip if interval_days)
```

## Quick start

```bash
git clone https://github.com/YOUR_USER/vacation-is-coming.git
cd vacation-is-coming

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r config/requirements.txt

cp config/.env.example config/.env
```

Edit `config/.env` (credentials) and `config/travel.yaml` (routes + schedule). The active
YAML is versioned in your fork; it does not contain secrets.

`config/travel.yaml` starts with `configured: false`, so flight searches cannot
run accidentally. Replace the starter values with your trip and set
`configured: true`, or ask an AI agent to do it for you.

```bash
# WhatsApp only (no flight search)
python -m src --test-whatsapp

# Search and print (no WhatsApp)
python -m src --dry-run

# Search and send
python -m src

# Force a run (ignore schedule.interval_days)
python -m src --force

# Sync the travel schedule → GitHub Actions UTC cron
python -m src --sync-schedule
```

## Use with any AI agent

1. Open this repo in Cursor, Claude Code, Codex, GPT, or similar.
2. Point the agent at [`AGENTS.md`](AGENTS.md) (Claude/Codex also read [`CLAUDE.md`](CLAUDE.md)).
3. Say what you want, for example:
   - “Monitor daily at 8am: JFK to Miami and Orlando, March 10–17 2027”
   - “Use range mode: cheapest 3 days between Feb 5–14, 7-day trip”
   - “Use explore mode for Salvador in February — cheapest week”
   - “Only alert me if Miami is under $350”
   - “Search every 3 days to save SerpAPI quota”
   - “Publish to git” / “Push my config”
4. The agent asks for any missing route details, then updates
   `config/preferences.md` + `config/travel.yaml`, sets `configured: true`, and
   syncs the schedule when needed.

Detailed checklists:

- [`agents/onboarding.md`](agents/onboarding.md) — first-time setup
- [`agents/monitor-flights.md`](agents/monitor-flights.md) — routes, dates, schedule
- [`agents/git.md`](agents/git.md) — commit and push to your remote
- [`skills/`](skills/) — thin adapters (see [`skills/README.md`](skills/README.md))

## Date modes

Set `search_mode` in `config/travel.yaml`:

| Mode | When to use | Config |
|------|-------------|--------|
| `fixed` | You know exact travel dates | `departure_date` / `return_date` on each route |
| `explore` | Flexible — cheapest week in a month (SerpAPI only) | `explore.month`, `explore.travel_duration`, `explore.deepen` |
| `range` | Cheapest departure days inside a window (SerpAPI only) | `range.departure_window_start/end`, `trip_duration_days`, `top_combinations` |

```yaml
search_mode: range
range:
  departure_window_start: "2027-02-05"
  departure_window_end: "2027-02-14"   # max 10-day window
  trip_duration_days: 7
  top_combinations: 3
schedule:
  interval_days: 3   # optional — ~10 runs/month for a 10-day × 2-route range config
```

```yaml
search_mode: explore
explore:
  month: 2              # February
  travel_duration: 2    # 1=weekend, 2=1 week, 3=2 weeks
  deepen: true          # also fetch top offers on the best dates found
```

Explore uses SerpAPI’s calendar API (~6 month horizon). Range uses one `google_flights` call per departure day per route. See [`docs/FLIGHT_PROVIDERS.md`](docs/FLIGHT_PROVIDERS.md).

## Publish to Git (git agent)

After the agent changes your config locally, push to **your fork** so GitHub Actions runs with the new routes.

1. Copy [`config/repo.example.yaml`](config/repo.example.yaml) → `config/repo.yaml` and set `configured: true` with your repo URL and branch.
2. In chat, say **“publish to git”** or **“git agent”** — the agent follows [`agents/git.md`](agents/git.md).
3. If Git is not set up yet, the agent asks for: repo URL, branch, clone status, and how you authenticate (`gh auth`, SSH, etc.). It never commits `config/.env` or API keys.

```yaml
# config/repo.yaml
configured: true
remote_url: "https://github.com/YOUR_USER/vacation-is-coming.git"
branch: main
remote_name: origin
```

Skill adapter: [`skills/git/SKILL.md`](skills/git/SKILL.md). Cursor users: create a local `.cursor/skills` → `skills/` link (see [`skills/README.md`](skills/README.md)).

## Credentials

### Flight prices (SerpAPI — default)

See [`docs/SETUP_SERPAPI.md`](docs/SETUP_SERPAPI.md). Amadeus enterprise BYOK: [`docs/SETUP_AMADEUS.md`](docs/SETUP_AMADEUS.md).

| Secret / variable | Description |
|-------------------|-------------|
| `FLIGHT_PROVIDER` | `serpapi` (default) or `amadeus` |
| `SERPAPI_API_KEY` | API key from [serpapi.com](https://serpapi.com) |

### WhatsApp (CallMeBot — simplest)

See [`docs/SETUP_WHATSAPP.md`](docs/SETUP_WHATSAPP.md).

| Variable | Description |
|----------|-------------|
| `WHATSAPP_PROVIDER` | `callmebot` (default) or `twilio` |
| `CALLMEBOT_PHONE` | Phone with country code |
| `CALLMEBOT_APIKEY` | Key from CallMeBot |

Twilio: set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `TWILIO_WHATSAPP_TO`.

## GitHub Actions

Workflow: [`.github/workflows/check-prices.yml`](.github/workflows/check-prices.yml)

- Runs on a daily cron (synced from `config/travel.yaml` via `--sync-schedule`); respects `schedule.interval_days` (skips SerpAPI on off days)
- Manual **Run workflow** always searches immediately (`--force`)
- Commits each search run's price snapshot to `config/snapshots/`

Repository secrets (`Settings → Secrets and variables → Actions`):

| Secret | Required | Description |
|--------|----------|-------------|
| `SERPAPI_API_KEY` | yes (SerpAPI) | SerpAPI API key |
| `FLIGHT_PROVIDER` | no | `serpapi` (default) or `amadeus` |
| `AMADEUS_CLIENT_ID` | if Amadeus | Enterprise API key |
| `AMADEUS_CLIENT_SECRET` | if Amadeus | Enterprise API secret |
| `AMADEUS_ENV` | if Amadeus | `production` |
| `WHATSAPP_PROVIDER` | no | `callmebot` or `twilio` |
| `CALLMEBOT_PHONE` | if CallMeBot | Phone with country code |
| `CALLMEBOT_APIKEY` | if CallMeBot | CallMeBot API key |
| `TWILIO_*` | if Twilio | Twilio credentials |
| `PRICE_ALERT_MAX` | no | Only send when an offer is ≤ this value |

The schedule is a static UTC cron. For timezones that observe daylight saving
time, run `python -m src --sync-schedule` and commit the workflow after each
DST transition.

## Example messages

**WhatsApp (range mode — top 3 per route):**

```text
*Flight price alert — Salvador Fev/2027*
Ida 05/02-14/02 · 7 dias · top 3

*Londrina → Salvador*

*1.* R$ 1.316
   11/02 -> 18/02
   Azul · 1 escala · 5h15
   caiu R$ 254 vs ultima

*2.* R$ 1.333
   ...
```

**WhatsApp (fixed / explore — summary vs last run):**

```text
Flight price alert — Example trip
Mode: fixed dates

Vs last: 1 down, 1 up, 0 flat
Cheapest today:
• JFK → MIA: 10-Mar-17-Mar · USD 420 (-30 vs last)
```

**Snapshot (full detail in repo):** comparison table + top offers per route in `config/snapshots/`.

## Project layout

```text
vacation-is-coming/
├── README.md
├── AGENTS.md              # contract for any AI agent
├── config/
│   ├── .env.example
│   ├── requirements.txt
│   ├── travel.yaml        # active, versioned configuration
│   ├── travel.example.yaml
│   ├── repo.yaml          # git publish target (your fork)
│   ├── repo.example.yaml
│   └── preferences.md     # free-text preferences for agents
├── agents/                # AI-agent playbooks
│   ├── onboarding.md
│   ├── monitor-flights.md
│   ├── git.md
│   └── itineraries.md
├── skills/                # thin skill adapters (vendor-neutral)
│   ├── README.md
│   ├── fare-alerts/
│   └── git/
├── src/
│   ├── config.py
│   ├── history.py         # price comparison from snapshots
│   ├── flights/           # SerpAPI (default) + Amadeus BYOK
│   ├── whatsapp.py
│   ├── schedule.py
│   ├── snapshot.py
│   ├── main.py
│   └── __main__.py
├── docs/
│   ├── GUIA_REPASSE.md    # full handoff guide (Portuguese)
│   ├── SETUP_SERPAPI.md
│   ├── SETUP_WHATSAPP.md
│   ├── SETUP_AMADEUS.md
│   └── FLIGHT_PROVIDERS.md
├── dev/
│   └── tests/
│       ├── test_main.py
│       ├── test_serpapi.py
│       └── test_history.py
└── .github/workflows/
    └── check-prices.yml
```

## Handoff / repasse (Português)

Guia completo para passar o projeto para outra pessoa (do zero ao WhatsApp):
[`docs/GUIA_REPASSE.md`](docs/GUIA_REPASSE.md)

## Tests

```bash
pip install -r config/requirements.txt pytest
python -m pytest -q
```

## Roadmap

Day-by-day **itineraries** (activities, lodging ideas) are planned for a later release. See [`agents/itineraries.md`](agents/itineraries.md).
