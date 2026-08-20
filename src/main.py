"""Entry point: search flight prices and send a WhatsApp alert."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from .config import Settings, load_settings
from .flights import FlightOffer, search_all_routes
from .history import PriceHistory, load_history, price_delta, should_run_interval
from .schedule import explain_schedule, sync_workflow_cron
from .snapshot import save_snapshot
from .whatsapp import send_whatsapp


def format_duration(iso_duration: str) -> str:
    """Convert PT5H30M to 5h30m."""
    text = iso_duration.replace("PT", "")
    hours = minutes = 0
    if "H" in text:
        hours_part, text = text.split("H", 1)
        hours = int(hours_part or 0)
    if "M" in text:
        minutes = int(text.replace("M", "") or 0)
    if hours and minutes:
        return f"{hours}h{minutes:02d}m"
    if hours:
        return f"{hours}h"
    if minutes:
        return f"{minutes}m"
    return iso_duration


def _group_offers(offers: list[FlightOffer]) -> dict[str, list[FlightOffer]]:
    by_route: dict[str, list[FlightOffer]] = defaultdict(list)
    for offer in offers:
        by_route[offer.route_name].append(offer)
    for route_offers in by_route.values():
        route_offers.sort(key=lambda o: o.price)
    return dict(by_route)


def _format_dates(offer: FlightOffer) -> str:
    if offer.return_date:
        return f"{offer.departure_date} -> {offer.return_date}"
    return offer.departure_date


def _format_dates_short(offer: FlightOffer) -> str:
    try:
        dep = datetime.strptime(offer.departure_date, "%Y-%m-%d")
        dep_text = dep.strftime("%d-%b")
        if offer.return_date:
            ret = datetime.strptime(offer.return_date, "%Y-%m-%d")
            return f"{dep_text}-{ret.strftime('%d-%b')}"
        return dep_text
    except ValueError:
        return _format_dates(offer)


def _delta_note(
    price: float,
    history: PriceHistory | None,
    route_name: str,
) -> str:
    if history is None:
        return ""

    parts: list[str] = []
    delta = price_delta(price, history.previous.get(route_name))
    if delta is not None:
        sign = "+" if delta > 0 else ""
        parts.append(f"{sign}{delta:.0f} vs last")
    min_7d = history.min_7d.get(route_name)
    if min_7d is not None:
        parts.append(f"7d min {min_7d:,.0f}")
    return f" ({', '.join(parts)})" if parts else ""


def _format_stops(offer: FlightOffer) -> str:
    return "nonstop" if offer.stops_outbound == 0 else f"{offer.stops_outbound} stop(s)"


def _format_offer_detail(offer: FlightOffer) -> str:
    duration = format_duration(offer.duration_outbound)
    return f"{offer.airline} ({_format_stops(offer)}, {duration})"


def _search_mode_header(settings: Settings) -> str:
    if settings.search_mode == "explore" and settings.explore is not None:
        month_names = (
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        )
        month = month_names[settings.explore.month - 1]
        return f"Mode: explore - best week in {month}"
    if settings.search_mode == "range" and settings.range is not None:
        window = settings.range
        try:
            start = datetime.strptime(window.departure_window_start, "%Y-%m-%d").strftime("%d-%b")
            end = datetime.strptime(window.departure_window_end, "%Y-%m-%d").strftime("%d-%b")
            window_text = f"{start} to {end}"
        except ValueError:
            window_text = f"{window.departure_window_start} to {window.departure_window_end}"
        return (
            f"Mode: range - {window_text} "
            f"({window.trip_duration_days}d trip, top {window.top_combinations})"
        )
    return "Mode: fixed dates"


def format_full_alert_body(
    settings: Settings,
    offers: list[FlightOffer],
    history: PriceHistory | None = None,
) -> str:
    if not offers:
        return f"{settings.message_title}\n\nNo offers found for the configured routes."

    lines = [settings.message_title, _search_mode_header(settings), ""]
    for route_name, route_offers in _group_offers(offers).items():
        best = route_offers[0]
        dates = best.departure_date
        if best.return_date:
            dates = f"{best.departure_date} -> {best.return_date}"

        if settings.search_mode == "range":
            lines.append(f"*{route_name}* — top {len(route_offers)}")
        else:
            lines.append(f"*{route_name}* ({dates})")
        for idx, offer in enumerate(route_offers[:3], start=1):
            delta = _delta_note(offer.price, history, route_name) if idx == 1 else ""
            if settings.search_mode == "range":
                lines.append(
                    f"{idx}. {_format_dates_short(offer)} · {offer.currency} {offer.price:,.2f}{delta} — "
                    f"{_format_offer_detail(offer)}"
                )
            else:
                lines.append(
                    f"{idx}. {offer.currency} {offer.price:,.2f}{delta} — "
                    f"{_format_offer_detail(offer)}"
                )
        lines.append("")

    if settings.price_alert_max is not None:
        lines.append(f"Configured limit: {settings.price_alert_max:,.2f}")

    return "\n".join(lines).rstrip()


def format_whatsapp_message(
    settings: Settings,
    offers: list[FlightOffer],
    history: PriceHistory | None = None,
) -> str:
    if not offers:
        return f"{settings.message_title}\n\nNo offers found for the configured routes."

    grouped = _group_offers(offers)
    best_by_route = {name: route_offers[0] for name, route_offers in grouped.items()}

    deltas: list[tuple[str, FlightOffer, float]] = []
    for route_name, offer in best_by_route.items():
        if history is None:
            continue
        delta = price_delta(offer.price, history.previous.get(route_name))
        if delta is not None:
            deltas.append((route_name, offer, delta))

    down = sum(1 for _, _, d in deltas if d < 0)
    up = sum(1 for _, _, d in deltas if d > 0)
    flat = sum(1 for _, _, d in deltas if d == 0)

    lines = [settings.message_title, _search_mode_header(settings), ""]
    if history and history.previous:
        lines.append(f"Vs last: {down} down, {up} up, {flat} flat")
        if deltas:
            biggest_drop = min(deltas, key=lambda item: item[2])
            biggest_rise = max(deltas, key=lambda item: item[2])
            if biggest_drop[2] < 0:
                lines.append(
                    f"Biggest drop: {biggest_drop[0]} {biggest_drop[2]:+.0f}"
                )
            if biggest_rise[2] > 0:
                lines.append(
                    f"Biggest rise: {biggest_rise[0]} {biggest_rise[2]:+.0f}"
                )
        lines.append("")

    def route_line(route_name: str, offer: FlightOffer) -> str:
        note = _delta_note(offer.price, history, route_name)
        return (
            f"• {route_name}: {_format_dates_short(offer)} · "
            f"{offer.currency} {offer.price:,.0f}{note}"
        )

    drops = sorted(
        ((name, offer, delta) for name, offer, delta in deltas if delta < 0),
        key=lambda item: item[2],
    )[:3]
    if drops:
        lines.append("Top drops:")
        for route_name, offer, _ in drops:
            lines.append(route_line(route_name, offer))
        lines.append("")

    rises = sorted(
        ((name, offer, delta) for name, offer, delta in deltas if delta > 0),
        key=lambda item: item[2],
        reverse=True,
    )[:3]
    if rises:
        lines.append("Top rises:")
        for route_name, offer, _ in rises:
            lines.append(route_line(route_name, offer))
        lines.append("")

    cheapest = sorted(best_by_route.items(), key=lambda item: item[1].price)[:5]
    lines.append("Cheapest today:")
    for route_name, offer in cheapest:
        lines.append(route_line(route_name, offer))
    lines.append("")
    lines.append("Full history: config/snapshots/")

    if settings.price_alert_max is not None:
        lines.append(f"Configured limit: {settings.price_alert_max:,.2f}")

    return "\n".join(lines).rstrip()


def format_message(
    settings: Settings,
    offers: list[FlightOffer],
    history: PriceHistory | None = None,
) -> str:
    """Backward-compatible alias for the full alert body."""
    return format_full_alert_body(settings, offers, history)


def should_notify(settings: Settings, offers: list[FlightOffer]) -> bool:
    if not offers:
        return True
    if settings.price_alert_max is None:
        return True
    return any(offer.price <= settings.price_alert_max for offer in offers)


def run(dry_run: bool = False, config_path: Path | None = None, *, force: bool = False) -> int:
    preview = load_settings(config_path, require_routes=False, require_flights=False)
    if not preview.configured:
        print(
            "Skipping search: flight monitoring is not configured. "
            "Set origin, destinations, and dates in config/travel.yaml, "
            "then set configured: true."
        )
        return 0

    settings = load_settings(config_path)

    interval_days = settings.schedule.interval_days
    if interval_days and not force and not dry_run:
        should_run, reason = should_run_interval(interval_days)
        if not should_run:
            print(reason)
            return 0
        if reason != "no previous snapshot":
            print(reason)

    captured_at = datetime.now(UTC)
    history = load_history(before=captured_at)
    offers = search_all_routes(settings)

    whatsapp_message = format_whatsapp_message(settings, offers, history)
    full_body = format_full_alert_body(settings, offers, history)

    snapshot_path = save_snapshot(
        settings,
        full_body,
        captured_at=captured_at,
        history=history,
        offers=offers,
    )
    print(f"Snapshot saved: {snapshot_path}")
    print(whatsapp_message)
    print()

    if dry_run:
        print("[dry-run] Message not sent.")
        return 0

    if not should_notify(settings, offers):
        cheapest = min(offers, key=lambda o: o.price)
        print(
            f"Lowest price ({cheapest.price:.2f}) is above the limit "
            f"({settings.price_alert_max:.2f}). WhatsApp not sent; snapshot saved."
        )
        return 0

    parts = send_whatsapp(settings, whatsapp_message)
    print(f"WhatsApp message sent ({parts} part(s)).")
    return 0


def run_whatsapp_test(config_path: Path | None = None) -> int:
    """Send a test message without calling a flight provider."""
    settings = load_settings(
        config_path,
        require_flights=False,
        require_routes=False,
    )
    message = (
        "*vacation-is-coming — WhatsApp test OK*\n"
        "If you received this, WhatsApp alerts are configured."
    )
    print(message)
    print()
    send_whatsapp(settings, message)
    print("Test message sent via WhatsApp.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search flight prices and send the result via WhatsApp."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Search and print the result without sending WhatsApp.",
    )
    parser.add_argument(
        "--test-whatsapp",
        action="store_true",
        help="Send only a WhatsApp test message (no flight search).",
    )
    parser.add_argument(
        "--sync-schedule",
        action="store_true",
        help="Update GitHub Actions cron from config/travel.yaml (local tz → UTC).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if schedule.interval_days has not elapsed since the last snapshot.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a travel YAML file (default: config/travel.yaml).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.sync_schedule:
            print(explain_schedule(args.config))
            cron = sync_workflow_cron(args.config)
            print(f"Workflow cron updated: {cron}")
            return 0
        if args.test_whatsapp:
            return run_whatsapp_test(config_path=args.config)
        return run(dry_run=args.dry_run, config_path=args.config, force=args.force)
    except Exception as exc:  # noqa: BLE001 — CLI should report any failure
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
