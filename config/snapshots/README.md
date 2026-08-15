# Price snapshots

Each search run (or manual workflow with `--force`) saves a Markdown file here:

`YYYY-MM-DD-HHMMSS.md`

When `schedule.interval_days` is set, the cron still fires daily but most days skip without creating a new snapshot.

Each file includes:

- Metadata (capture time, search mode)
- **Comparison** table: best price per route vs last run and 7-day minimum
- Full route details (top 3 offers per route)

WhatsApp receives a shorter summary; the snapshot is the full history.

Files are committed automatically by GitHub Actions so you can browse price history in the repo.
