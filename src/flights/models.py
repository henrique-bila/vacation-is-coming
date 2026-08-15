"""Shared flight offer model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FlightOffer:
    route_name: str
    origin: str
    destination: str
    departure_date: str
    return_date: str | None
    price: float
    currency: str
    airline: str
    stops_outbound: int
    duration_outbound: str
