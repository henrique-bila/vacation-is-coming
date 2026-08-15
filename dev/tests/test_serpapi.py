"""Tests for SerpAPI response parsing."""

from src.config import ExploreSettings, RangeSettings, Route, Schedule, Settings
from src.flights.serpapi import SerpApiClient


def _route() -> Route:
    return Route(
        name="Londrina → Maceió",
        origin="LDB",
        destination="MCZ",
        departure_date="2027-03-10",
        return_date="2027-03-17",
        adults=1,
        currency="BRL",
        max_results=3,
    )


def test_parse_serpapi_offers():
    payload = {
        "best_flights": [
            {"flights": [{"airline": "A"}], "total_duration": 100, "price": 100},
            {"flights": [{"airline": "B"}], "total_duration": 100, "price": 200},
            {"flights": [{"airline": "C"}], "total_duration": 100, "price": 300},
            {"flights": [{"airline": "D"}], "total_duration": 100, "price": 400},
        ],
    }
    route = Route(
        name="Test",
        origin="LDB",
        destination="MCZ",
        departure_date="2027-03-10",
        return_date="2027-03-17",
        adults=1,
        currency="BRL",
        max_results=2,
    )
    offers = SerpApiClient._parse_offers(route, payload)
    assert len(offers) == 2
    assert offers[0].price == 100.0


def test_is_no_results_error():
    from src.flights.serpapi import _is_no_results_error

    assert _is_no_results_error("Google Flights hasn't returned any results for this query.")
    assert not _is_no_results_error("Invalid API key")


def test_parse_explore_offers():
    route = _route()
    flights = [
        {
            "price": 1500,
            "airline": "Azul",
            "number_of_stops": 1,
            "duration": 370,
        },
        {
            "price": 1800,
            "airline": "LATAM",
            "number_of_stops": 0,
            "duration": 300,
        },
    ]
    offers = SerpApiClient._parse_explore_offers(
        route,
        flights,
        departure_date="2027-03-12",
        return_date="2027-03-19",
    )
    assert len(offers) == 2
    assert offers[0].price == 1500.0
    assert offers[0].departure_date == "2027-03-12"
    assert offers[0].return_date == "2027-03-19"
    assert offers[0].airline == "Azul"


def _explore_settings() -> Settings:
    return Settings(
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
        message_title="test",
        schedule=Schedule(timezone="America/Sao_Paulo", hour=8, minute=0),
        search_mode="explore",
        explore=ExploreSettings(month=2, travel_duration=2, deepen=True),
        range=None,
    )


def test_search_explore_falls_back_on_api_error():
    client = SerpApiClient(_explore_settings())
    engines: list[str] = []

    def fake_get_json(params):
        engine = str(params.get("engine"))
        engines.append(engine)
        if engine == "google_travel_explore":
            raise RuntimeError("SerpAPI HTTP 400: Invalid month")
        return {
            "best_flights": [
                {"flights": [{"airline": "Azul"}], "total_duration": 300, "price": 1400},
            ]
        }

    client._get_json = fake_get_json  # type: ignore[method-assign]
    offers = client.search_explore(_route())
    assert engines == ["google_travel_explore", "google_flights"]
    assert len(offers) == 1
    assert offers[0].price == 1400.0
    assert offers[0].departure_date == "2027-03-10"


def _range_settings() -> Settings:
    return Settings(
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
        message_title="test",
        schedule=Schedule(timezone="America/Sao_Paulo", hour=8, minute=0),
        search_mode="range",
        explore=None,
        range=RangeSettings(
            departure_window_start="2027-02-05",
            departure_window_end="2027-02-07",
            trip_duration_days=7,
            top_combinations=3,
        ),
    )


def test_search_range_returns_top_three_cheapest_days():
    client = SerpApiClient(_range_settings())
    searched_dates: list[str] = []

    def fake_search(route: Route):
        searched_dates.append(route.departure_date)
        price_by_day = {
            "2027-02-05": 1800.0,
            "2027-02-06": 1500.0,
            "2027-02-07": 1400.0,
        }
        price = price_by_day[route.departure_date]
        return [
            SerpApiClient._parse_offers(
                route,
                {
                    "best_flights": [
                        {
                            "flights": [{"airline": "Azul"}],
                            "total_duration": 300,
                            "price": price,
                        }
                    ]
                },
            )[0]
        ]

    client.search = fake_search  # type: ignore[method-assign]
    offers = client.search_range(_route())
    assert searched_dates == ["2027-02-05", "2027-02-06", "2027-02-07"]
    assert len(offers) == 3
    assert offers[0].price == 1400.0
    assert offers[0].departure_date == "2027-02-07"
    assert offers[0].return_date == "2027-02-14"
    assert offers[2].price == 1800.0
