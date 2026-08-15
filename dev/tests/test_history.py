"""Tests for price history parsing."""

from datetime import UTC, datetime
from pathlib import Path

from src.history import (
    load_history,
    parse_snapshot_best_prices,
    parse_snapshot_timestamp,
    should_run_interval,
)


SAMPLE_SNAPSHOT = """\
# Flight price alert — Nordeste Mar/2027

- **Captured at (UTC):** 2026-08-04 13:07:09

---

## Londrina → Recife (2027-03-10 -> 2027-03-17)
1. BRL 1,213.00 — Azul (1 stop(s), 5h45m)
2. BRL 1,550.00 — LATAM (1 stop(s), 6h55m)

## Londrina → Salvador (2027-03-10 -> 2027-03-17)
1. BRL 1,204.00 — LATAM (1 stop(s), 9h35m)
"""


def test_parse_snapshot_best_prices(tmp_path: Path):
    path = tmp_path / "2026-08-04-130709.md"
    path.write_text(SAMPLE_SNAPSHOT, encoding="utf-8")

    prices = parse_snapshot_best_prices(path)
    assert prices["Londrina → Recife"] == 1213.0
    assert prices["Londrina → Salvador"] == 1204.0


def test_load_history_previous_and_min_7d(tmp_path: Path):
    older = tmp_path / "2026-08-03-120000.md"
    older.write_text(
        SAMPLE_SNAPSHOT.replace("1,213.00", "1,300.00").replace("1,204.00", "1,100.00"),
        encoding="utf-8",
    )
    newer = tmp_path / "2026-08-04-130709.md"
    newer.write_text(SAMPLE_SNAPSHOT, encoding="utf-8")

    history = load_history(
        snapshots_dir=tmp_path,
        before=datetime(2026, 8, 5, 13, 0, 0, tzinfo=UTC),
        window_days=7,
    )

    assert history.previous["Londrina → Recife"] == 1213.0
    assert history.min_7d["Londrina → Recife"] == 1213.0
    assert history.min_7d["Londrina → Salvador"] == 1100.0


def test_load_history_empty_when_no_snapshots(tmp_path: Path):
    history = load_history(
        snapshots_dir=tmp_path,
        before=datetime(2026, 8, 5, 13, 0, 0, tzinfo=UTC),
    )
    assert history.previous == {}
    assert history.min_7d == {}


def test_parse_snapshot_timestamp():
    assert parse_snapshot_timestamp("2026-08-15-201438") == datetime(
        2026, 8, 15, 20, 14, 38, tzinfo=UTC
    )
    assert parse_snapshot_timestamp("bad-name") is None


def test_should_run_interval_without_snapshots(tmp_path: Path):
    ok, reason = should_run_interval(3, snapshots_dir=tmp_path)
    assert ok is True
    assert reason == "no previous snapshot"


def test_should_run_interval_skips_before_elapsed(tmp_path: Path):
    snap = tmp_path / "2026-08-15-120000.md"
    snap.write_text("# test\n", encoding="utf-8")
    now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=UTC)
    ok, reason = should_run_interval(3, now=now, snapshots_dir=tmp_path)
    assert ok is False
    assert "skipped" in reason


def test_should_run_interval_runs_after_elapsed(tmp_path: Path):
    snap = tmp_path / "2026-08-12-120000.md"
    snap.write_text("# test\n", encoding="utf-8")
    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
    ok, reason = should_run_interval(3, now=now, snapshots_dir=tmp_path)
    assert ok is True
    assert "last snapshot" in reason
