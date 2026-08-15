"""Persist flight price alert snapshots as Markdown files."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .config import Settings
from .flights.models import FlightOffer
from .history import PriceHistory, price_delta

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS_DIR = ROOT / "config" / "snapshots"


def whatsapp_message_to_markdown(message: str) -> str:
    """Convert WhatsApp-style *bold* route headers to Markdown headings."""
    lines: list[str] = []
    for line in message.splitlines():
        if line.startswith("*") and "*" in line[1:]:
            end = line.index("*", 1)
            route = line[1:end]
            rest = line[end + 1 :].strip()
            heading = f"## {route}{(' ' + rest) if rest else ''}"
            lines.append(heading)
        else:
            lines.append(line)
    return "\n".join(lines).rstrip()


def _format_delta_cell(delta: float | None) -> str:
    if delta is None:
        return "—"
    return f"{delta:+,.2f}"


def build_comparison_table(
    offers: list[FlightOffer],
    history: PriceHistory | None,
) -> str:
    best_by_route: dict[str, FlightOffer] = {}
    for offer in offers:
        current = best_by_route.get(offer.route_name)
        if current is None or offer.price < current.price:
            best_by_route[offer.route_name] = offer

    if not best_by_route:
        return ""

    rows = [
        "## Comparison",
        "",
        "| Route | Dates | Today | vs last | 7d min |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for route_name in sorted(best_by_route):
        offer = best_by_route[route_name]
        dates = offer.departure_date
        if offer.return_date:
            dates = f"{offer.departure_date} -> {offer.return_date}"

        prev = history.previous.get(route_name) if history else None
        min_7d = history.min_7d.get(route_name) if history else None
        delta = price_delta(offer.price, prev)

        rows.append(
            f"| {route_name} | {dates} | {offer.price:,.2f} | "
            f"{_format_delta_cell(delta)} | "
            f"{f'{min_7d:,.2f}' if min_7d is not None else '—'} |"
        )

    return "\n".join(rows)


def build_snapshot_markdown(
    settings: Settings,
    full_body: str,
    *,
    captured_at: datetime,
    history: PriceHistory | None = None,
    offers: list[FlightOffer] | None = None,
) -> str:
    """Build a Markdown snapshot with metadata, comparison table, and route details."""
    body_lines = full_body.splitlines()
    alert_body = "\n".join(body_lines[2:]).strip() if len(body_lines) > 2 else ""
    alert_md = whatsapp_message_to_markdown(alert_body) if alert_body else "_No offers found._"
    comparison = build_comparison_table(offers or [], history) if offers else ""

    mode_line = f"- **Search mode:** {settings.search_mode}"
    if settings.search_mode == "explore" and settings.explore is not None:
        mode_line += (
            f" (month={settings.explore.month}, "
            f"duration={settings.explore.travel_duration}, "
            f"deepen={str(settings.explore.deepen).lower()})"
        )
    if settings.search_mode == "range" and settings.range is not None:
        window = settings.range
        mode_line += (
            f" ({window.departure_window_start} to {window.departure_window_end}, "
            f"trip={window.trip_duration_days}d, top={window.top_combinations})"
        )

    sections = [
        f"# {settings.message_title}",
        "",
        f"- **Captured at (UTC):** {captured_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Schedule timezone:** {settings.schedule.timezone}",
        mode_line,
        "",
        "---",
        "",
    ]
    if comparison:
        sections.extend([comparison, "", "---", ""])
    sections.append(alert_md)
    sections.append("")
    return "\n".join(sections)


def save_snapshot(
    settings: Settings,
    full_body: str,
    *,
    captured_at: datetime | None = None,
    history: PriceHistory | None = None,
    offers: list[FlightOffer] | None = None,
) -> Path:
    """Write the alert snapshot to config/snapshots/YYYY-MM-DD-HHMMSS.md."""
    when = captured_at or datetime.now(UTC)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOTS_DIR / f"{when.strftime('%Y-%m-%d-%H%M%S')}.md"
    path.write_text(
        build_snapshot_markdown(
            settings,
            full_body,
            captured_at=when,
            history=history,
            offers=offers,
        ),
        encoding="utf-8",
    )
    return path
