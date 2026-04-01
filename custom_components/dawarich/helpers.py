"""Helper functions for the Dawarich integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientSession
from dawarich_api import DawarichAPI


@dataclass(slots=True)
class DawarichArea:
    """Representation of a Dawarich area."""

    name: str
    latitude: float
    longitude: float
    radius: int
    area_id: int | None = None


def get_base_url(host: str, use_ssl: bool) -> str:
    """Build the Dawarich base URL."""
    url = host.removeprefix("http://").removeprefix("https://")
    if use_ssl:
        return f"https://{url}"
    return f"http://{url}"


def get_api(host: str, api_key: str, use_ssl: bool, verify_ssl: bool) -> DawarichAPI:
    """Get the API object."""
    return DawarichAPI(
        url=get_base_url(host, use_ssl), api_key=api_key, verify_ssl=verify_ssl
    )


async def async_get_areas(
    session: ClientSession, base_url: str, api_key: str, verify_ssl: bool
) -> list[DawarichArea]:
    """Fetch all areas from Dawarich."""
    async with session.get(
        f"{base_url}/api/v1/areas",
        params={"api_key": api_key},
        ssl=verify_ssl,
    ) as response:
        response.raise_for_status()
        payload = await response.json()

    areas: list[DawarichArea] = []
    for item in payload:
        try:
            areas.append(
                DawarichArea(
                    area_id=int(item["id"]),
                    name=str(item["name"]),
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                    radius=int(float(item["radius"])),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    return areas


async def async_create_area(
    session: ClientSession,
    base_url: str,
    api_key: str,
    verify_ssl: bool,
    area: DawarichArea,
) -> None:
    """Create a Dawarich area."""
    async with session.post(
        f"{base_url}/api/v1/areas",
        params={"api_key": api_key},
        json={
            "area": {
                "name": area.name,
                "latitude": area.latitude,
                "longitude": area.longitude,
                "radius": area.radius,
            }
        },
        ssl=verify_ssl,
    ) as response:
        response.raise_for_status()


async def async_update_area(
    session: ClientSession,
    base_url: str,
    api_key: str,
    verify_ssl: bool,
    area: DawarichArea,
) -> None:
    """Update a Dawarich area."""
    if area.area_id is None:
        msg = "Area ID is required to update a Dawarich area"
        raise ValueError(msg)

    async with session.patch(
        f"{base_url}/api/v1/areas/{area.area_id}",
        params={"api_key": api_key},
        json={
            "area": {
                "name": area.name,
                "latitude": area.latitude,
                "longitude": area.longitude,
                "radius": area.radius,
            }
        },
        ssl=verify_ssl,
    ) as response:
        response.raise_for_status()


def areas_match(first: DawarichArea, second: DawarichArea) -> bool:
    """Return whether two areas already have equivalent values."""
    return (
        abs(first.latitude - second.latitude) < 0.000001
        and abs(first.longitude - second.longitude) < 0.000001
        and first.radius == second.radius
    )
