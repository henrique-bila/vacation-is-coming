---
name: fare-alerts
description: >-
  Adapter for vacation-is-coming: flight price monitoring and WhatsApp alerts.
  Use when the user asks to change routes, dates, destinations, price limits,
  schedule, test CallMeBot, or update config/preferences.md / config/travel.yaml.
  Follow AGENTS.md — do not duplicate that contract here.
---

# fare-alerts

Thin skill adapter. **Follow [`AGENTS.md`](../../AGENTS.md)** and the playbooks under `agents/`.

## Quick pointers

- Preferences: `config/preferences.md`
- Executable config: `config/travel.yaml` (template: `config/travel.example.yaml`)
- Date modes: `search_mode: fixed` (exact dates), `explore` (best week in month), or `range` (best days in a window — ask window, trip duration, top N)
- Optional `schedule.interval_days` to save SerpAPI quota; manual Actions run uses `--force`
- Before searching, collect missing trip details and set `configured: true`
- Onboarding: `agents/onboarding.md`
- Flight monitoring: `agents/monitor-flights.md`
- Itineraries: phase 2 only — `agents/itineraries.md`
- After schedule edits: `python -m src --sync-schedule`
- Never commit `config/.env` or API keys
