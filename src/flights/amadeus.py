"""Flight offer search via Amadeus Flight Offers Search (enterprise BYOK)."""

from __future__ import annotations

import requests

from ..config import Route, Settings
from .models import FlightOffer

TOKEN_URL = {
    "test": "https://test.api.amadeus.com/v1/security/oauth2/token",
    "production": "https://api.amadeus.com/v1/security/oauth2/token",
}
SEARCH_URL = {
    "test": "https://test.api.amadeus.com/v2/shopping/flight-offers",
    "production": "https://api.amadeus.com/v2/shopping/flight-offers",
}


class AmadeusClient:
    def __init__(self, settings: Settings) -> None:
        if settings.amadeus_env not in TOKEN_URL:
            raise ValueError("AMADEUS_ENV must be 'test' or 'production'")
        self._settings = settings
        self._token: str | None = None

    def _base(self, mapping: dict[str, str]) -> str:
        return mapping[self._settings.amadeus_env]

    def authenticate(self) -> str:
        response = requests.post(
            self._base(TOKEN_URL),
            data={
                "grant_type": "client_credentials",
                "client_id": self._settings.amadeus_client_id,
                "client_secret": self._settings.amadeus_client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("Amadeus did not return access_token")
        self._token = token
        return token

    def _headers(self) -> dict[str, str]:
        if not self._token:
            self.authenticate()
        assert self._token
        return {"Authorization": f"Bearer {self._token}"}

    def search(self, route: Route) -> list[FlightOffer]:
        params: dict[str, str | int] = {
            "originLocationCode": route.origin,
            "destinationLocationCode": route.destination,
            "departureDate": route.departure_date,
            "adults": route.adults,
            "currencyCode": route.currency,
            "max": route.max_results,
            "nonStop": "false",
        }
        if route.return_date:
            params["returnDate"] = route.return_date

        response = requests.get(
            self._base(SEARCH_URL),
            headers=self._headers(),
            params=params,
            timeout=45,
        )
        if response.status_code == 401:
            self.authenticate()
            response = requests.get(
                self._base(SEARCH_URL),
                headers=self._headers(),
                params=params,
                timeout=45,
            )
        response.raise_for_status()
        return self._parse_offers(route, response.json())

    @staticmethod
    def _parse_offers(route: Route, payload: dict) -> list[FlightOffer]:
        dictionaries = payload.get("dictionaries") or {}
        carriers = dictionaries.get("carriers") or {}
        offers: list[FlightOffer] = []

        for item in payload.get("data") or []:
            price_info = item.get("price") or {}
            itineraries = item.get("itineraries") or []
            if not itineraries:
                continue

            outbound = itineraries[0]
            segments = outbound.get("segments") or []
            carrier_code = (segments[0].get("carrierCode") if segments else "") or ""
            airline = carriers.get(carrier_code, carrier_code) or "N/A"
            stops = max(len(segments) - 1, 0)

            try:
                price = float(price_info.get("grandTotal") or price_info.get("total") or 0)
            except (TypeError, ValueError):
                continue

            offers.append(
                FlightOffer(
                    route_name=route.name,
                    origin=route.origin,
                    destination=route.destination,
                    departure_date=route.departure_date,
                    return_date=route.return_date,
                    price=price,
                    currency=str(price_info.get("currency") or route.currency),
                    airline=str(airline),
                    stops_outbound=stops,
                    duration_outbound=str(outbound.get("duration") or "?"),
                )
            )

        offers.sort(key=lambda o: o.price)
        return offers


def search_all_routes(settings: Settings) -> list[FlightOffer]:
    client = AmadeusClient(settings)
    client.authenticate()
    results: list[FlightOffer] = []
    for route in settings.routes:
        results.extend(client.search(route))
    return results
