# Agent playbook — monitor flights

Primary v1 specialty: turn natural-language trip preferences into config and schedule.

## Interpret user requests

**Always ask which date mode the user wants when setting up or changing dates:**

- **`fixed`** — exact departure/return dates on every route (`departure_date`, `return_date`).
- **`explore`** — SerpAPI `google_travel_explore` finds the cheapest week in a month (`search_mode: explore`, `explore.month`, `explore.travel_duration`, optional `explore.deepen`). Requires `FLIGHT_PROVIDER=serpapi`. Horizon is ~6 months ahead.
- **`range`** — Search each departure day in a window (max **10 days**), fixed trip length, return the **top N** cheapest combinations with duration and stops (`search_mode: range`, `range.departure_window_start/end`, `range.trip_duration_days`, `range.top_combinations`). Requires `FLIGHT_PROVIDER=serpapi`. ~1 API call per day per route per run.

| User request | Action |
|--------------|--------|
| New destination (e.g. Atlanta) | Add a route with IATA (`ATL`) and same default origin/dates unless specified |
| Remove destination | Remove that route |
| Change dates (fixed) | Set `search_mode: fixed`; update `departure_date` / `return_date` on all active routes (unless one route only) |
| Cheapest days in a window (e.g. Feb 5–15, 7-day trip, top 3) | Ask **departure window** (max 10 days), **trip duration**, and **top N**; set `search_mode: range`; configure `range.*` |
| Cheapest week in March / flexible dates | Set `search_mode: explore`; configure `explore.month`, `travel_duration`, `deepen`; remind ~6 month horizon and API cost (~2× calls when `deepen: true`) |
| Change origin | Update `origin` (JFK, LHR, GRU, etc.) |
| “Only alert below X” | Document in `config/preferences.md`; remind `PRICE_ALERT_MAX=X` |
| “Send every day” | Clear / omit `PRICE_ALERT_MAX` |
| “Every day at 7am in São Paulo” | Set `schedule.timezone`, `hour`, `minute`; run `python -m src --sync-schedule` |
| “Every 3 days to save API quota” | Set `schedule.interval_days: 3` (cron stays daily; script skips until interval elapsed). Manual **Actions → Run workflow** always uses `--force` |
| Test WhatsApp | `python -m src --test-whatsapp` |

## Useful IATA codes

- New York `JFK`/`EWR`/`LGA` · Miami `MIA` · Orlando `MCO` · Atlanta `ATL`
- London `LHR` · Lisbon `LIS` · São Paulo `GRU`/`CGH` · Londrina `LDB`
- Maceió `MCZ` · Recife `REC` · Salvador `SSA` · Fortaleza `FOR` · Natal `NAT`

Dates in YAML: `YYYY-MM-DD`.

## Config shape

```yaml
configured: true
search_mode: fixed   # fixed | explore | range (explore/range require SerpAPI)
message_title: "Flight price alert — Example trip"
schedule:
  timezone: America/New_York
  hour: 8
  minute: 0
  interval_days: 3   # optional — skip API until N days after last snapshot
# range:
#   departure_window_start: "2027-02-05"
#   departure_window_end: "2027-02-14"
#   trip_duration_days: 7
#   top_combinations: 3
# explore:
#   month: 3
#   travel_duration: 2   # 1=weekend, 2=1 week, 3=2 weeks
#   deepen: true
routes:
  - name: "New York → Miami"
    origin: JFK
    destination: MIA
    departure_date: "2027-03-10"
    return_date: "2027-03-17"
    adults: 1
    currency: USD
    max_results: 5
```

`config/travel.yaml` is versioned in each fork and is the only route configuration
used by GitHub Actions. Do not use a secret to override it.

## After edits

1. Update `config/preferences.md` to match.
2. If schedule changed: `python -m src --sync-schedule`.
3. Suggest `--dry-run` before relying on production WhatsApp.
4. Remind the user to push so Actions picks up changes.
