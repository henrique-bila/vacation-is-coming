"""Flight search providers."""

from __future__ import annotations

from ..config import Settings
from . import amadeus, serpapi
from .models import FlightOffer

__all__ = ["FlightOffer", "search_all_routes"]


def search_all_routes(settings: Settings) -> list[FlightOffer]:
    provider = settings.flight_provider
    if provider == "serpapi":
        return serpapi.search_all_routes(settings)
    if provider == "amadeus":
        return amadeus.search_all_routes(settings)
    raise ValueError(
        f"Invalid FLIGHT_PROVIDER: {provider!r}. Use 'serpapi' or 'amadeus'."
    )
