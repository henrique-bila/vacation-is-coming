"""Tests for Markdown snapshot persistence."""

from datetime import UTC, datetime
from pathlib import Path

from src.config import Schedule
from src.history import PriceHistory
from src.main import format_full_alert_body
from src.snapshot import build_comparison_table, build_snapshot_markdown, save_snapshot, whatsapp_message_to_markdown
from dev.tests.test_main import _offer, _settings


def test_whatsapp_message_to_markdown_converts_route_headers():
    text = "*Londrina → Recife* (2027-03-10 -> 2027-03-17)\n1. BRL 1,294.00"
    assert "## Londrina → Recife (2027-03-10 -> 2027-03-17)" in whatsapp_message_to_markdown(text)


def test_build_comparison_table():
    offers = [
        _offer(1294.0, route_name="Londrina → Recife"),
        _offer(1100.0, route_name="Londrina → Salvador"),
    ]
    history = PriceHistory(
        previous={"Londrina → Recife": 1213.0},
        min_7d={"Londrina → Recife": 1100.0, "Londrina → Salvador": 1050.0},
    )
    table = build_comparison_table(offers, history)

    assert "## Comparison" in table
    assert "Londrina → Recife" in table
    assert "+81.00" in table
    assert "1,100.00" in table


def test_build_snapshot_markdown_includes_metadata_and_comparison():
    settings = _settings(
        message_title="Flight price alert — Nordeste Mar/2027",
        schedule=Schedule(timezone="America/Sao_Paulo", hour=8, minute=0),
    )
    offers = [_offer(1294.0, route_name="Londrina → Recife")]
    history = PriceHistory(previous={"Londrina → Recife": 1213.0}, min_7d={"Londrina → Recife": 1100.0})
    full_body = format_full_alert_body(settings, offers, history)
    captured_at = datetime(2026, 7, 28, 23, 7, 0, tzinfo=UTC)
    md = build_snapshot_markdown(
        settings,
        full_body,
        captured_at=captured_at,
        history=history,
        offers=offers,
    )

    assert "# Flight price alert — Nordeste Mar/2027" in md
    assert "**Captured at (UTC):** 2026-07-28 23:07:00" in md
    assert "America/Sao_Paulo" in md
    assert "**Search mode:** fixed" in md
    assert "## Comparison" in md
    assert "## Londrina → Recife" in md
    assert "USD 1,294.00" in md


def test_save_snapshot_writes_file(tmp_path: Path, monkeypatch):
    snapshots_dir = tmp_path / "snapshots"
    monkeypatch.setattr("src.snapshot.SNAPSHOTS_DIR", snapshots_dir)

    settings = _settings()
    offers = [_offer()]
    full_body = format_full_alert_body(settings, offers)
    captured_at = datetime(2026, 7, 28, 8, 0, 0, tzinfo=UTC)
    path = save_snapshot(
        settings,
        full_body,
        captured_at=captured_at,
        offers=offers,
    )

    assert path.name == "2026-07-28-080000.md"
    assert path.exists()
    assert "Flight price alert" in path.read_text(encoding="utf-8")
