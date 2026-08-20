# Agent contract — vacation-is-coming

This repository is **vacation-is-coming**: an open-source flight price monitor that searches Google Flights (SerpAPI) and sends WhatsApp alerts. It is designed for **any AI coding agent** (Cursor, Claude, Codex, GPT, etc.).

## Source of truth

1. Read [`config/preferences.md`](config/preferences.md) for the user's preferences (free text).
2. Apply changes to **both**:
   - `config/preferences.md` — human-readable preferences
   - `config/travel.yaml` — the versioned source of truth used by the script / Actions
3. After changing `schedule`, run `python -m src --sync-schedule` and commit the workflow change.
4. For price limits, document in `config/preferences.md` and remind the user about the Secret / `config/.env` key `PRICE_ALERT_MAX` (never commit `config/.env`).
5. For publish/push requests, follow [`agents/git.md`](agents/git.md) and read `config/repo.yaml` first.

Playbooks:

- [`agents/onboarding.md`](agents/onboarding.md) — first-time setup
- [`agents/monitor-flights.md`](agents/monitor-flights.md) — interpret natural language → config
- [`agents/git.md`](agents/git.md) — commit and push to the user's configured remote
- [`agents/itineraries.md`](agents/itineraries.md) — phase 2 (not implemented)

Thin skill adapters (triggers / pointers only): [`skills/`](skills/) — see [`skills/README.md`](skills/README.md).

## What you must do

1. **Onboarding** — First check whether `config/travel.yaml` has `configured: true`. If not, ask for origin, destinations, **date mode** (`fixed` exact dates, `explore` cheapest week in a month, or `range` cheapest days in a departure window), passengers, currency, alert time, and timezone. For `range`, also ask window (max 10 days), trip duration, and top N. Then guide SerpAPI ([`docs/SETUP_SERPAPI.md`](docs/SETUP_SERPAPI.md)) and WhatsApp ([`docs/SETUP_WHATSAPP.md`](docs/SETUP_WHATSAPP.md)). Do not ask users to paste API keys into long chat transcripts; point them at GitHub Secrets. Handoff guide (PT): [`docs/GUIA_REPASSE.md`](docs/GUIA_REPASSE.md).
2. **Monitoring** — On requests like “check every day at 8am for A, B, C”, update `config/preferences.md` + `config/travel.yaml` + sync the Actions cron. For SerpAPI quota, suggest `schedule.interval_days` (cron stays daily; script skips until elapsed).
3. **Run** — Suggest `python -m src --dry-run`, `python -m src --test-whatsapp`, `python -m src --force` (local override of interval), or a manual GitHub Actions run (workflow dispatch always uses `--force`).
4. **Security** — Never commit `config/.env`, CallMeBot keys, or SerpAPI / Amadeus API keys.
5. **Scope** — v1 is flight search + alerts only. Full day-by-day itineraries (hotels, attractions) are phase 2; say so and stay focused on destinations, dates, and price.

## Capabilities (v1)

| Capability | How |
|------------|-----|
| Search flights | `src/flights/` via SerpAPI (default) or Amadeus BYOK |
| Date modes | `fixed` (exact dates), `explore` (best week in month), `range` (best days in a window — SerpAPI only) |
| Price comparison | WhatsApp summary vs last run + 7d min; full table in `config/snapshots/` |
| WhatsApp alert | CallMeBot (default) or Twilio; compact summary vs last run (all modes) |
| Price snapshots | `config/snapshots/*.md` (auto-committed by Actions) |
| Schedule | `schedule` in `config/travel.yaml` → `python -m src --sync-schedule`; optional `interval_days` to skip API calls between runs |
| Optional price cap | `PRICE_ALERT_MAX` env / Secret |

## Response style

- Confirm changes in a few short lines (routes / dates / schedule / limit).
- Say explicitly when a push, merge, or GitHub Secret is required.
- Match the user's language in chat; keep repository files in English.
