"""Flight price search via SerpAPI Google Flights engine."""

from __future__ import annotations

from datetime import date, timedelta

import requests

from ..config import Route, Settings, iter_range_departure_dates
from .models import FlightOffer

SERPAPI_URL = "https://serpapi.com/search"


def _is_no_results_error(message: str) -> bool:
    lowered = message.lower()
    return "hasn't returned any results" in lowered or "no results" in lowered


def _minutes_to_iso_duration(minutes: int) -> str:
    hours, mins = divmod(max(minutes, 0), 60)
    if hours and mins:
        return f"PT{hours}H{mins}M"
    if hours:
        return f"PT{hours}H"
    if mins:
        return f"PT{mins}M"
    return "PT0M"


def _airline_label(flights: list[dict]) -> str:
    if not flights:
        return "N/A"
    names = {str(item.get("airline") or "").strip() for item in flights}
    names.discard("")
    if not names:
        return "N/A"
    if len(names) == 1:
        return names.pop()
    return "Multi"


def _stops_count(flight: dict) -> int:
    layovers = flight.get("layovers") or []
    segments = flight.get("flights") or []
    if layovers:
        return len(layovers)
    return max(len(segments) - 1, 0)


class SerpApiClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _get_json(self, params: dict[str, str | int]) -> dict:
        response = requests.get(SERPAPI_URL, params=params, timeout=60)
        try:
            payload = response.json()
        except ValueError:
            response.raise_for_status()
            raise RuntimeError(
                f"SerpAPI returned non-JSON response ({response.status_code})"
            ) from None

        error = str(payload.get("error") or "").strip()
        if error:
            if _is_no_results_error(error):
                return {"_no_results": True, "error": error}
            if not response.ok:
                raise RuntimeError(f"SerpAPI HTTP {response.status_code}: {error}")
            raise RuntimeError(f"SerpAPI error: {error}")

        if not response.ok:
            response.raise_for_status()
        return payload

    def search(self, route: Route) -> list[FlightOffer]:
        params: dict[str, str | int] = {
            "engine": "google_flights",
            "api_key": self._settings.serpapi_api_key,
            "departure_id": route.origin,
            "arrival_id": route.destination,
            "outbound_date": route.departure_date,
            "currency": route.currency,
            "adults": route.adults,
            "hl": "en",
        }
        if route.return_date:
            params["type"] = 1  # round trip
            params["return_date"] = route.return_date
        else:
            params["type"] = 2  # one way

        payload = self._get_json(params)
        if payload.get("_no_results"):
            print(f"[{route.name}] No offers from Google Flights for this query.")
            return []
        return self._parse_offers(route, payload)

    def search_explore(self, route: Route) -> list[FlightOffer]:
        explore = self._settings.explore
        if explore is None:
            raise RuntimeError("explore settings missing while search_mode is explore")

        params: dict[str, str | int] = {
            "engine": "google_travel_explore",
            "api_key": self._settings.serpapi_api_key,
            "departure_id": route.origin,
            "arrival_id": route.destination,
            "month": explore.month,
            "travel_duration": explore.travel_duration,
            "currency": route.currency,
            "adults": route.adults,
            "hl": "en",
        }
        try:
            payload = self._get_json(params)
        except (requests.HTTPError, RuntimeError) as exc:
            print(f"[{route.name}] Explore failed ({exc}); trying configured dates.")
            return self.search(route)

        if payload.get("_no_results"):
            print(f"[{route.name}] Explore returned no results; trying configured dates.")
            return self.search(route)

        start_date = str(payload.get("start_date") or "").strip()
        end_date = str(payload.get("end_date") or "").strip() or None
        flights = payload.get("flights") or []

        if not start_date and not flights:
            print(f"[{route.name}] Explore returned no dates; trying configured dates.")
            return self.search(route)

        if explore.deepen and start_date:
            dated_route = Route(
                name=route.name,
                origin=route.origin,
                destination=route.destination,
                departure_date=start_date,
                return_date=end_date or route.return_date,
                adults=route.adults,
                currency=route.currency,
                max_results=route.max_results,
            )
            return self.search(dated_route)

        return self._parse_explore_offers(
            route,
            flights,
            departure_date=start_date or route.departure_date,
            return_date=end_date or route.return_date,
        )

    def search_range(self, route: Route) -> list[FlightOffer]:
        range_settings = self._settings.range
        if range_settings is None:
            raise RuntimeError("range settings missing while search_mode is range")

        candidates: list[FlightOffer] = []
        for departure in iter_range_departure_dates(range_settings):
            return_date = (
                date.fromisoformat(departure) + timedelta(days=range_settings.trip_duration_days)
            ).isoformat()
            dated_route = Route(
                name=route.name,
                origin=route.origin,
                destination=route.destination,
                departure_date=departure,
                return_date=return_date,
                adults=route.adults,
                currency=route.currency,
                max_results=route.max_results,
            )
            try:
                day_offers = self.search(dated_route)
            except (requests.HTTPError, RuntimeError) as exc:
                print(f"[{route.name}] Range skip {departure}: {exc}")
                continue
            if day_offers:
                candidates.append(day_offers[0])

        if not candidates:
            print(f"[{route.name}] Range search returned no offers for any departure day.")
            return []

        candidates.sort(key=lambda offer: offer.price)
        return candidates[: range_settings.top_combinations]

    @staticmethod
    def _parse_explore_offers(
        route: Route,
        flights: list[dict],
        *,
        departure_date: str,
        return_date: str | None,
    ) -> list[FlightOffer]:
        candidates: list[FlightOffer] = []
        for item in flights:
            try:
                price = float(item.get("price") or 0)
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue

            candidates.append(
                FlightOffer(
                    route_name=route.name,
                    origin=route.origin,
                    destination=route.destination,
                    departure_date=departure_date,
                    return_date=return_date,
                    price=price,
                    currency=route.currency,
                    airline=str(item.get("airline") or "N/A"),
                    stops_outbound=int(item.get("number_of_stops") or 0),
                    duration_outbound=_minutes_to_iso_duration(int(item.get("duration") or 0)),
                )
            )

        candidates.sort(key=lambda o: o.price)
        return candidates[: route.max_results]

    @staticmethod
    def _parse_offers(route: Route, payload: dict) -> list[FlightOffer]:
        candidates: list[FlightOffer] = []
        buckets = (payload.get("best_flights") or []) + (payload.get("other_flights") or [])

        for item in buckets:
            try:
                price = float(item.get("price") or 0)
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue

            segments = item.get("flights") or []
            total_minutes = int(item.get("total_duration") or 0)
            candidates.append(
                FlightOffer(
                    route_name=route.name,
                    origin=route.origin,
                    destination=route.destination,
                    departure_date=route.departure_date,
                    return_date=route.return_date,
                    price=price,
                    currency=route.currency,
                    airline=_airline_label(segments),
                    stops_outbound=_stops_count(item),
                    duration_outbound=_minutes_to_iso_duration(total_minutes),
                )
            )

        candidates.sort(key=lambda o: o.price)
        return candidates[: route.max_results]


def search_all_routes(settings: Settings) -> list[FlightOffer]:
    client = SerpApiClient(settings)
    results: list[FlightOffer] = []
    for route in settings.routes:
        if settings.search_mode == "explore":
            results.extend(client.search_explore(route))
        elif settings.search_mode == "range":
            results.extend(client.search_range(route))
        else:
            results.extend(client.search(route))
    return results
