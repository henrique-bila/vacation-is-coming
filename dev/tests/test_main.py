"""Unit tests for message formatting and schedule helpers."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.config import EXAMPLE_CONFIG_PATH, ExploreSettings, RangeSettings, Schedule, Settings, load_settings
from src.flights import FlightOffer
from src.history import PriceHistory
from src.main import (
    format_duration,
    format_full_alert_body,
    format_message,
    format_whatsapp_message,
    run,
    should_notify,
)
from src.schedule import local_to_utc_cron


def _settings(**overrides) -> Settings:
    base = dict(
        flight_provider="serpapi",
        serpapi_api_key="test-key",
        amadeus_client_id="",
        amadeus_client_secret="",
        amadeus_env="production",
        whatsapp_provider="callmebot",
        callmebot_phone="",
        callmebot_apikey="",
        twilio_account_sid="",
        twilio_auth_token="",
        twilio_whatsapp_from="",
        twilio_whatsapp_to="",
        price_alert_max=None,
        routes=[],
        message_title="Flight price alert — vacation-is-coming",
        schedule=Schedule(timezone="America/New_York", hour=8, minute=0),
        search_mode="fixed",
        explore=None,
        range=None,
    )
    base.update(overrides)
    return Settings(**base)


def _offer(price: float = 500.0, route_name: str = "JFK → MIA") -> FlightOffer:
    return FlightOffer(
        route_name=route_name,
        origin="JFK",
        destination="MIA",
        departure_date="2027-03-10",
        return_date="2027-03-17",
        price=price,
        currency="USD",
        airline="LATAM",
        stops_outbound=0,
        duration_outbound="PT3H10M",
    )


def test_format_duration():
    assert format_duration("PT5H30M") == "5h30m"
    assert format_duration("PT2H") == "2h"
    assert format_duration("PT45M") == "45m"


def test_format_message_includes_best_offers():
    message = format_message(_settings(), [_offer(420.5), _offer(510.0)])
    assert "Flight price alert — vacation-is-coming" in message
    assert "JFK → MIA" in message
    assert "USD 420.50" in message
    assert "LATAM" in message
    assert "nonstop" in message
    assert "Mode: fixed dates" in message


def test_format_whatsapp_message_is_lightweight():
    offers = [
        _offer(420.5, route_name="JFK → MIA"),
        _offer(510.0, route_name="JFK → MIA"),
        _offer(300.0, route_name="JFK → BOS"),
    ]
    history = PriceHistory(
        previous={"JFK → MIA": 450.0, "JFK → BOS": 280.0},
        min_7d={"JFK → MIA": 400.0, "JFK → BOS": 250.0},
    )
    message = format_whatsapp_message(_settings(), offers, history)

    assert "Cheapest today:" in message
    assert "Vs last:" in message
    assert "Full history: config/snapshots/" in message
    assert "2. USD" not in message
    assert "3. USD" not in message


def test_format_full_alert_body_includes_delta_on_best_offer():
    history = PriceHistory(previous={"JFK → MIA": 450.0}, min_7d={"JFK → MIA": 400.0})
    message = format_full_alert_body(_settings(), [_offer(420.5)], history)
    assert "-30 vs last" in message
    assert "7d min 400" in message


def test_format_whatsapp_explore_mode_header():
    settings = _settings(
        search_mode="explore",
        explore=ExploreSettings(month=3, travel_duration=1, deepen=True),
    )
    message = format_whatsapp_message(settings, [_offer()], None)
    assert "Mode: explore - best week in Mar" in message


def test_format_whatsapp_range_mode_uses_same_summary_as_other_modes():
    settings = _settings(
        search_mode="range",
        range=RangeSettings(
            departure_window_start="2027-02-05",
            departure_window_end="2027-02-14",
            trip_duration_days=7,
            top_combinations=3,
        ),
    )
    offers = [
        _offer(1400.0, route_name="LDB → SSA"),
        _offer(1500.0, route_name="LDB → SSA"),
        _offer(1600.0, route_name="LDB → SSA"),
    ]
    message = format_whatsapp_message(settings, offers, None)
    assert "Mode: range - 05-Feb to 14-Feb (7d trip, top 3)" in message
    assert "Cheapest today:" in message
    assert "• LDB → SSA: 10-Mar-17-Mar · USD 1,400" in message
    assert "*1.*" not in message
    assert "caiu R$" not in message
    assert "Full history: config/snapshots/" in message


def test_format_whatsapp_range_mode_shows_delta_on_best():
    settings = _settings(
        search_mode="range",
        range=RangeSettings(
            departure_window_start="2027-02-05",
            departure_window_end="2027-02-14",
            trip_duration_days=7,
            top_combinations=3,
        ),
    )
    offers = [_offer(1316.0, route_name="Londrina → Salvador")]
    history = PriceHistory(previous={"Londrina → Salvador": 1570.0}, min_7d={})
    message = format_whatsapp_message(settings, offers, history)
    assert "-254 vs last" in message
    assert "caiu R$" not in message


def test_format_full_alert_body_range_mode():
    settings = _settings(
        search_mode="range",
        range=RangeSettings(
            departure_window_start="2027-02-05",
            departure_window_end="2027-02-14",
            trip_duration_days=7,
            top_combinations=3,
        ),
    )
    message = format_full_alert_body(settings, [_offer(1400.0, route_name="LDB → SSA")], None)
    assert "top 1" in message
    assert "10-Mar-17-Mar" in message
    assert "nonstop" in message


def test_should_notify_respects_price_limit():
    settings = _settings(price_alert_max=400.0)
    assert should_notify(settings, [_offer(350.0)]) is True
    assert should_notify(settings, [_offer(450.0)]) is False
    assert should_notify(_settings(price_alert_max=None), [_offer(999.0)]) is True


def test_local_to_utc_cron_sao_paulo():
    schedule = Schedule(timezone="America/Sao_Paulo", hour=8, minute=0)
    ref = datetime(2026, 7, 26, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    cron = local_to_utc_cron(schedule, reference=ref)
    assert cron == "0 11 * * *"


def test_default_configuration_blocks_unconfigured_search(tmp_path: Path):
    config = tmp_path / "travel.yaml"
    config.write_text("configured: false\nschedule:\n  timezone: UTC\n  hour: 8\n  minute: 0\nroutes: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Flight monitoring is not configured"):
        load_settings(config, require_flights=False)


def test_run_skips_unconfigured_search(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    config = tmp_path / "travel.yaml"
    config.write_text(
        "configured: false\nschedule:\n  timezone: UTC\n  hour: 8\n  minute: 0\nroutes: []\n",
        encoding="utf-8",
    )
    assert run(dry_run=True, config_path=config) == 0
    captured = capsys.readouterr()
    assert "Skipping search" in captured.out
    assert "not configured" in captured.out


def test_default_configuration_requires_serpapi_for_search(tmp_path: Path):
    config = tmp_path / "travel.yaml"
    config.write_text(
        EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="SERPAPI_API_KEY"):
        load_settings(config, require_flights=True)


def test_default_configuration_is_available_for_whatsapp_only():
    settings = load_settings(EXAMPLE_CONFIG_PATH, require_flights=False, require_routes=False)
    assert len(settings.routes) >= 1
    assert settings.schedule.timezone == "America/New_York"
    assert settings.search_mode == "fixed"


def test_explore_mode_requires_explore_block(tmp_path: Path, monkeypatch):
    config = tmp_path / "travel.yaml"
    config.write_text(
        "configured: true\nsearch_mode: explore\nschedule:\n  timezone: UTC\n  hour: 8\n  minute: 0\n"
        "routes:\n  - name: Test\n    origin: JFK\n    destination: MIA\n    departure_date: '2027-03-10'\n"
        "    return_date: '2027-03-17'\n    adults: 1\n    currency: USD\n    max_results: 3\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    with pytest.raises(ValueError, match="explore.month"):
        load_settings(config, require_flights=True)


def test_range_mode_requires_range_block(tmp_path: Path, monkeypatch):
    config = tmp_path / "travel.yaml"
    config.write_text(
        "configured: true\nsearch_mode: range\nschedule:\n  timezone: UTC\n  hour: 8\n  minute: 0\n"
        "routes:\n  - name: Test\n    origin: JFK\n    destination: MIA\n    departure_date: '2027-03-10'\n"
        "    return_date: '2027-03-17'\n    adults: 1\n    currency: USD\n    max_results: 3\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    with pytest.raises(ValueError, match="departure_window_start"):
        load_settings(config, require_flights=True)


def test_range_mode_rejects_window_over_ten_days(tmp_path: Path, monkeypatch):
    config = tmp_path / "travel.yaml"
    config.write_text(
        "configured: true\nsearch_mode: range\nschedule:\n  timezone: UTC\n  hour: 8\n  minute: 0\n"
        "range:\n  departure_window_start: '2027-02-05'\n  departure_window_end: '2027-02-15'\n"
        "  trip_duration_days: 7\n  top_combinations: 3\n"
        "routes:\n  - name: Test\n    origin: JFK\n    destination: MIA\n    adults: 1\n"
        "    currency: USD\n    max_results: 3\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    with pytest.raises(ValueError, match="maximum is 10"):
        load_settings(config, require_flights=True)
