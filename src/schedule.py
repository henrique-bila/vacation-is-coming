"""Sync config/travel.yaml schedule to the GitHub Actions cron (UTC)."""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .config import DEFAULT_CONFIG_PATH, EXAMPLE_CONFIG_PATH, ROOT, Schedule

WORKFLOW_PATH = ROOT / ".github" / "workflows" / "check-prices.yml"

CRON_COMMENT = (
    "# Cron is generated from config schedule (local tz → UTC). "
    "Run: python -m src --sync-schedule"
)


def local_to_utc_cron(schedule: Schedule, reference: datetime | None = None) -> str:
    """Convert local hour/minute in schedule.timezone to a daily UTC cron expression."""
    tz = ZoneInfo(schedule.timezone)
    ref = reference or datetime.now(tz=tz)
    local_dt = datetime(
        ref.year,
        ref.month,
        ref.day,
        schedule.hour,
        schedule.minute,
        tzinfo=tz,
    )
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
    # GitHub Actions cron has no seconds; minute/hour only
    return f"{utc_dt.minute} {utc_dt.hour} * * *"


def load_schedule_from_config(config_path: Path | None = None) -> Schedule:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        path = EXAMPLE_CONFIG_PATH
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    block = raw.get("schedule") or {}
    return Schedule(
        timezone=str(block.get("timezone") or "America/Sao_Paulo"),
        hour=int(block.get("hour", 8)),
        minute=int(block.get("minute", 0)),
        interval_days=(
            int(block["interval_days"])
            if block.get("interval_days") is not None
            else None
        ),
    )


def sync_workflow_cron(
    config_path: Path | None = None,
    workflow_path: Path | None = None,
) -> str:
    """Update the workflow cron from config/travel.yaml. Returns the cron used."""
    schedule = load_schedule_from_config(config_path)
    cron = local_to_utc_cron(schedule)
    path = workflow_path or WORKFLOW_PATH
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")

    text = path.read_text(encoding="utf-8")
    replacement = (
        f"schedule:\n"
        f"    {CRON_COMMENT}\n"
        f'    - cron: "{cron}"'
    )
    block_pattern = re.compile(
        r"schedule:\s*\n(?:\s*#.*\n)*\s*-\s*cron:\s*\"[^\"]+\"",
        re.MULTILINE,
    )
    if not block_pattern.search(text):
        raise RuntimeError("Could not find schedule.cron in workflow file")

    new_text = block_pattern.sub(replacement, text, count=1)
    path.write_text(new_text, encoding="utf-8")
    return cron


def explain_schedule(config_path: Path | None = None) -> str:
    schedule = load_schedule_from_config(config_path)
    cron = local_to_utc_cron(schedule)
    tz = ZoneInfo(schedule.timezone)
    now = datetime.now(tz=tz)
    local_dt = datetime(now.year, now.month, now.day, schedule.hour, schedule.minute, tzinfo=tz)
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
    interval = schedule.interval_days
    interval_line = (
        f"Every {interval} days (cron still daily; skips until interval elapsed)"
        if interval
        else "Every day"
    )
    return (
        f"Local: {schedule.hour:02d}:{schedule.minute:02d} ({schedule.timezone})\n"
        f"UTC:   {utc_dt.hour:02d}:{utc_dt.minute:02d}\n"
        f"Cron:  {cron}\n"
        f"Runs:  {interval_line}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync config/travel.yaml schedule to GitHub Actions cron (UTC)."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a travel YAML file (default: config/travel.yaml).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the cron that would be written without editing the workflow.",
    )
    args = parser.parse_args(argv)
    print(explain_schedule(args.config))
    if args.dry_run:
        return 0
    cron = sync_workflow_cron(args.config)
    print(f"Updated {WORKFLOW_PATH} with cron: {cron}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
