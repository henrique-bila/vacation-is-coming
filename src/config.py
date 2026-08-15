"""Load environment and YAML configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config" / "travel.yaml"
EXAMPLE_CONFIG_PATH = ROOT / "config" / "travel.example.yaml"
ENV_PATH = ROOT / "config" / ".env"
MAX_RANGE_DEPARTURE_DAYS = 10


@dataclass(frozen=True)
class Route:
    name: str
    origin: str
    destination: str
    departure_date: str
    return_date: str | None
    adults: int
    currency: str
    max_results: int


@dataclass(frozen=True)
class Schedule:
    timezone: str
    hour: int
    minute: int
    interval_days: int | None = None


@dataclass(frozen=True)
class ExploreSettings:
    month: int
    travel_duration: int
    deepen: bool = True


@dataclass(frozen=True)
class RangeSettings:
    departure_window_start: str
    departure_window_end: str
    trip_duration_days: int
    top_combinations: int = 3


@dataclass(frozen=True)
class Settings:
    flight_provider: str
    serpapi_api_key: str
    amadeus_client_id: str
    amadeus_client_secret: str
    amadeus_env: str
    whatsapp_provider: str
    callmebot_phone: str
    callmebot_apikey: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str
    twilio_whatsapp_to: str
    price_alert_max: float | None
    routes: list[Route]
    message_title: str
    schedule: Schedule
    search_mode: str
    explore: ExploreSettings | None
    range: RangeSettings | None


def _require(name: str, value: str) -> str:
    if not value.strip():
        raise ValueError(f"Required environment variable missing: {name}")
    return value.strip()


def _parse_schedule(raw: dict[str, Any]) -> Schedule:
    block = raw.get("schedule") or {}
    hour = int(block.get("hour", 8))
    minute = int(block.get("minute", 0))
    if not 0 <= hour <= 23:
        raise ValueError("schedule.hour must be between 0 and 23")
    if not 0 <= minute <= 59:
        raise ValueError("schedule.minute must be between 0 and 59")
    interval_raw = block.get("interval_days")
    interval_days: int | None
    if interval_raw is None:
        interval_days = None
    else:
        interval_days = int(interval_raw)
        if interval_days < 1:
            raise ValueError("schedule.interval_days must be at least 1")
    return Schedule(
        timezone=str(block.get("timezone") or "America/Sao_Paulo"),
        hour=hour,
        minute=minute,
        interval_days=interval_days,
    )


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


def _parse_explore_settings(raw: dict[str, Any]) -> ExploreSettings:
    block = raw.get("explore") or {}
    month = int(block.get("month", 0))
    if not 1 <= month <= 12:
        raise ValueError("explore.month must be between 1 and 12 when search_mode is explore")

    travel_duration = int(block.get("travel_duration", 2))
    if travel_duration not in (1, 2, 3):
        raise ValueError("explore.travel_duration must be 1 (weekend), 2 (1 week), or 3 (2 weeks)")

    deepen = block.get("deepen", True)
    if not isinstance(deepen, bool):
        deepen = str(deepen).strip().lower() not in ("false", "0", "no")

    return ExploreSettings(
        month=month,
        travel_duration=travel_duration,
        deepen=deepen,
    )


def _parse_range_settings(raw: dict[str, Any]) -> RangeSettings:
    block = raw.get("range") or {}
    start_raw = str(block.get("departure_window_start") or "").strip()
    end_raw = str(block.get("departure_window_end") or "").strip()
    if not start_raw or not end_raw:
        raise ValueError(
            "range.departure_window_start and range.departure_window_end are required "
            "when search_mode is range"
        )

    start = _parse_date(start_raw, "range.departure_window_start")
    end = _parse_date(end_raw, "range.departure_window_end")
    if end < start:
        raise ValueError("range.departure_window_end must be on or after departure_window_start")

    window_days = (end - start).days + 1
    if window_days > MAX_RANGE_DEPARTURE_DAYS:
        raise ValueError(
            f"range window spans {window_days} departure days; maximum is {MAX_RANGE_DEPARTURE_DAYS}"
        )

    trip_duration_days = int(block.get("trip_duration_days", 0))
    if trip_duration_days < 1:
        raise ValueError("range.trip_duration_days must be at least 1")

    top_combinations = int(block.get("top_combinations", 3))
    if top_combinations < 1:
        raise ValueError("range.top_combinations must be at least 1")

    return RangeSettings(
        departure_window_start=start.isoformat(),
        departure_window_end=end.isoformat(),
        trip_duration_days=trip_duration_days,
        top_combinations=top_combinations,
    )


def iter_range_departure_dates(range_settings: RangeSettings) -> list[str]:
    """Return ISO departure dates from range start through end (inclusive)."""
    start = date.fromisoformat(range_settings.departure_window_start)
    end = date.fromisoformat(range_settings.departure_window_end)
    days: list[str] = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _parse_search_mode(
    raw: dict[str, Any],
    flight_provider: str,
) -> tuple[str, ExploreSettings | None, RangeSettings | None]:
    search_mode = str(raw.get("search_mode") or "fixed").strip().lower()
    if search_mode not in ("fixed", "explore", "range"):
        raise ValueError("search_mode must be 'fixed', 'explore', or 'range'")

    if search_mode == "fixed":
        return search_mode, None, None

    if flight_provider != "serpapi":
        raise ValueError(f"search_mode {search_mode} requires FLIGHT_PROVIDER=serpapi")

    if search_mode == "explore":
        return search_mode, _parse_explore_settings(raw), None

    return search_mode, None, _parse_range_settings(raw)


def load_settings(
    config_path: Path | None = None,
    *,
    require_flights: bool = True,
    require_routes: bool = True,
) -> Settings:
    load_dotenv(ENV_PATH)

    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        if EXAMPLE_CONFIG_PATH.exists():
            path = EXAMPLE_CONFIG_PATH
        else:
            raise FileNotFoundError(
                "No configuration found. Create config/travel.yaml from "
                "config/travel.example.yaml."
            )

    with path.open(encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    configured = raw.get("configured") is True
    search_mode = str(raw.get("search_mode") or "fixed").strip().lower()

    routes: list[Route] = []
    for item in raw.get("routes") or []:
        departure = str(item.get("departure_date") or "").strip()
        return_date_raw = item.get("return_date")
        return_date = str(return_date_raw).strip() if return_date_raw else None

        if search_mode == "fixed":
            if not departure:
                raise ValueError(f"Route {item.get('name')!r} requires departure_date in fixed mode")

        routes.append(
            Route(
                name=str(item["name"]),
                origin=str(item["origin"]).upper(),
                destination=str(item["destination"]).upper(),
                departure_date=departure or "1970-01-01",
                return_date=return_date,
                adults=int(item.get("adults") or 1),
                currency=str(item.get("currency") or "USD").upper(),
                max_results=int(item.get("max_results") or 5),
            )
        )

    if require_routes and not configured:
        raise ValueError(
            "Flight monitoring is not configured. Set your origin, destinations, "
            "and dates in config/travel.yaml, then set configured: true."
        )
    if require_routes and not routes:
        raise ValueError("Configure at least one route in config/travel.yaml")

    price_raw = os.getenv("PRICE_ALERT_MAX", "").strip()
    price_alert_max = float(price_raw) if price_raw else None

    flight_provider = (os.getenv("FLIGHT_PROVIDER") or "serpapi").strip().lower()
    serpapi_api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID", "").strip()
    amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET", "").strip()

    if require_flights:
        if flight_provider == "serpapi":
            serpapi_api_key = _require("SERPAPI_API_KEY", serpapi_api_key)
        elif flight_provider == "amadeus":
            amadeus_client_id = _require("AMADEUS_CLIENT_ID", amadeus_client_id)
            amadeus_client_secret = _require("AMADEUS_CLIENT_SECRET", amadeus_client_secret)
        else:
            raise ValueError(
                f"Invalid FLIGHT_PROVIDER: {flight_provider!r}. Use 'serpapi' or 'amadeus'."
            )

    search_mode, explore, range = _parse_search_mode(raw, flight_provider)

    return Settings(
        flight_provider=flight_provider,
        serpapi_api_key=serpapi_api_key,
        amadeus_client_id=amadeus_client_id,
        amadeus_client_secret=amadeus_client_secret,
        amadeus_env=(os.getenv("AMADEUS_ENV") or "test").strip().lower(),
        whatsapp_provider=(os.getenv("WHATSAPP_PROVIDER") or "callmebot").strip().lower(),
        callmebot_phone=os.getenv("CALLMEBOT_PHONE", "").strip(),
        callmebot_apikey=os.getenv("CALLMEBOT_APIKEY", "").strip(),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", "").strip(),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", "").strip(),
        twilio_whatsapp_from=os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886").strip(),
        twilio_whatsapp_to=os.getenv("TWILIO_WHATSAPP_TO", "").strip(),
        price_alert_max=price_alert_max,
        routes=routes,
        message_title=str(raw.get("message_title") or "Flight price alert — vacation-is-coming"),
        schedule=_parse_schedule(raw),
        search_mode=search_mode,
        explore=explore,
        range=range,
    )
