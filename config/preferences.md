# vacation-is-coming — monitoring preferences

Agents use this file plus `AGENTS.md` / `agents/` to update `travel.yaml`.

## Current preferences

*(Not configured yet — set `configured: true` in `config/travel.yaml` after adding routes.)*

- **Origins:** —
- **Destinations:** —
- **Search mode:** —
- **Schedule:** —
- **WhatsApp alerts:** yes (when configured)
- **Price limit (optional):** none
- **Execution:** GitHub Actions + repository Secrets

## Example chat instructions

- "Monitor JFK → Miami daily at 8am, March 10–17 2027"
- "Range mode: cheapest 3 days between Feb 5–14, 7-day trip"
- "Only notify me if price is under $350"
- "Search every 3 days to save SerpAPI quota"

## How to apply

1. Edit this file **or** ask your AI agent in chat.
2. The agent updates `travel.yaml` (and reminds you about GitHub Secrets if needed).
3. After schedule changes: `python -m src --sync-schedule`, then commit and push.
4. GitHub Actions cron runs daily; `interval_days` skips API calls between searches.
