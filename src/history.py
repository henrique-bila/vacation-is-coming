"""Load price history from previous Markdown snapshots."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .config import ROOT

SNAPSHOTS_DIR = ROOT / "config" / "snapshots"

PRICE_LINE_RE = re.compile(r"^1\.\s+[A-Z]{3}\s+([\d,]+\.\d{2})")
ROUTE_HEADING_RE = re.compile(r"^##\s+(.+?)(?:\s+\((.+?)\))?\s*$")


@dataclass(frozen=True)
class PriceHistory:
    previous: dict[str, float]
    min_7d: dict[str, float]


def parse_snapshot_best_prices(path: Path) -> dict[str, float]:
    """Extract the best (line 1) price per route from a snapshot file."""
    text = path.read_text(encoding="utf-8")
    prices: dict[str, float] = {}
    current_route: str | None = None

    for line in text.splitlines():
        stripped = line.strip()
        heading = ROUTE_HEADING_RE.match(stripped)
        if heading:
            title = heading.group(1).strip()
            if title == "Comparison":
                current_route = None
                continue
            current_route = title
            continue

        if current_route:
            match = PRICE_LINE_RE.match(stripped)
            if match:
                prices[current_route] = float(match.group(1).replace(",", ""))
                current_route = None

    return prices


def load_history(
    *,
    snapshots_dir: Path = SNAPSHOTS_DIR,
    before: datetime | None = None,
    window_days: int = 7,
) -> PriceHistory:
    """Load previous-run prices and rolling minimum over window_days."""
    when = before or datetime.now(UTC)
    before_stamp = when.strftime("%Y-%m-%d-%H%M%S")
    cutoff_stamp = (when - timedelta(days=window_days)).strftime("%Y-%m-%d-%H%M%S")

    files = sorted(
        path
        for path in snapshots_dir.glob("*.md")
        if path.name != "README.md" and path.stem < before_stamp
    )

    previous: dict[str, float] = {}
    if files:
        previous = parse_snapshot_best_prices(files[-1])

    min_7d: dict[str, float] = {}
    for path in files:
        if path.stem < cutoff_stamp:
            continue
        for route, price in parse_snapshot_best_prices(path).items():
            if route not in min_7d or price < min_7d[route]:
                min_7d[route] = price

    return PriceHistory(previous=previous, min_7d=min_7d)


def price_delta(current: float, baseline: float | None) -> float | None:
    if baseline is None:
        return None
    return current - baseline


def parse_snapshot_timestamp(stem: str) -> datetime | None:
    """Parse snapshot filename stem YYYY-MM-DD-HHMMSS as UTC."""
    parts = stem.split("-")
    if len(parts) != 4 or len(parts[3]) != 6:
        return None
    try:
        return datetime(
            int(parts[0]),
            int(parts[1]),
            int(parts[2]),
            int(parts[3][:2]),
            int(parts[3][2:4]),
            int(parts[3][4:6]),
            tzinfo=UTC,
        )
    except ValueError:
        return None


def latest_snapshot_at(snapshots_dir: Path = SNAPSHOTS_DIR) -> datetime | None:
    latest: datetime | None = None
    for path in snapshots_dir.glob("*.md"):
        if path.name == "README.md":
            continue
        captured = parse_snapshot_timestamp(path.stem)
        if captured and (latest is None or captured > latest):
            latest = captured
    return latest


def should_run_interval(
    interval_days: int,
    *,
    now: datetime | None = None,
    snapshots_dir: Path = SNAPSHOTS_DIR,
) -> tuple[bool, str]:
    """Return whether enough time passed since the last snapshot to search again."""
    when = now or datetime.now(UTC)
    latest = latest_snapshot_at(snapshots_dir)
    if latest is None:
        return True, "no previous snapshot"

    elapsed = when - latest
    if elapsed >= timedelta(days=interval_days):
        return True, f"last snapshot {latest.strftime('%Y-%m-%d %H:%M UTC')}"

    remaining = timedelta(days=interval_days) - elapsed
    days_left = remaining.total_seconds() / 86400
    return (
        False,
        f"skipped — next run in ~{days_left:.1f}d "
        f"(interval {interval_days}d, last {latest.strftime('%Y-%m-%d')})",
    )
