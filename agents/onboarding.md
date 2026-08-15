# Agent playbook — onboarding

Use this when a new user clones vacation-is-coming and needs to get alerts working.

## Checklist

1. **Clone / fork** the repository and open it in any AI coding tool.
2. **Python env**
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r config/requirements.txt
   ```
3. **Configuration** — `config/travel.yaml` starts with `configured: false`.
   Ask for the user's origin, destinations, **date mode** (`fixed`, `explore`, or `range`), travel dates or window/duration/top-N, passengers, currency,
   alert time, timezone, and optional `interval_days` for SerpAPI quota. Set `configured: true` only after writing their
   choices. Full human guide: [`docs/GUIA_REPASSE.md`](../docs/GUIA_REPASSE.md).
   ```bash
   cp config/.env.example config/.env
   ```
   Edit `config/travel.yaml`. This is the active configuration and should be
   committed in the user's fork; credentials remain only in `config/.env` or GitHub Secrets.
4. **WhatsApp** — follow [`docs/SETUP_WHATSAPP.md`](../docs/SETUP_WHATSAPP.md), then:
   ```bash
   python -m src --test-whatsapp
   ```
5. **SerpAPI** — follow [`docs/SETUP_SERPAPI.md`](../docs/SETUP_SERPAPI.md). Add `SERPAPI_API_KEY` and `FLIGHT_PROVIDER=serpapi` as GitHub Secrets. Optional local test:
   ```bash
   python -m src --dry-run
   ```
6. **Schedule** — set `schedule` in `config/travel.yaml` / `config/preferences.md`, then:
   ```bash
   python -m src --sync-schedule
   ```
7. **GitHub Secrets** — see the table in the root `README.md`. Run the workflow once via **Actions → Run workflow** (manual runs always use `--force`).
8. **Natural language** — user can say: “Monitor daily at 8am: JFK → MIA and MCO, Mar 10–17 2027” or “Cheapest 3 days in Feb 5–14, 7-day trip”. Apply via [`monitor-flights.md`](monitor-flights.md).

## Agent reminders

- Never commit `config/.env`.
- Default flight provider is **SerpAPI** (`FLIGHT_PROVIDER=serpapi`).
- Free SerpAPI tier: 250 searches/month — cost depends on mode: `fixed` ≈ 1× routes; `range` ≈ window_days × routes; `explore` ≈ 1–2× routes. Use `schedule.interval_days` to reduce runs (cron stays daily; script skips).
- Manual **Actions → Run workflow** bypasses `interval_days` (`--force`).
- This environment may not be able to create GitHub Secrets (403). Tell the user to add them in the GitHub UI.
- GitHub Actions uses a static UTC cron. After a daylight-saving transition, run
  `python -m src --sync-schedule` again and commit the workflow.
