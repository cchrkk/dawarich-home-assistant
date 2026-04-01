"""Zone synchronization helpers for the Dawarich integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp import ClientResponseError
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .helpers import (
    DawarichArea,
    areas_match,
    async_create_area,
    async_get_areas,
    async_update_area,
    get_base_url,
)
from .const import (
    CONF_AUTO_SYNC_ZONES,
    CONF_SYNC_ZONES,
)

if TYPE_CHECKING:
    from custom_components.dawarich import DawarichConfigEntry

_LOGGER = logging.getLogger(__name__)


def get_selected_zone_entity_ids(entry: config_entries.ConfigEntry) -> set[str]:
    """Return the configured zone entity ids, or an empty set for all zones."""
    configured_zones = entry.options.get(
        CONF_SYNC_ZONES, entry.data.get(CONF_SYNC_ZONES, [])
    )
    if isinstance(configured_zones, str):
        return {configured_zones}
    if isinstance(configured_zones, list):
        return {zone for zone in configured_zones if isinstance(zone, str)}
    return set()


def collect_home_assistant_zones(
    hass: HomeAssistant, selected_zone_entity_ids: set[str] | None = None
) -> list[DawarichArea]:
    """Return syncable Home Assistant zones."""
    zones: list[DawarichArea] = []
    for zone_state in hass.states.async_all("zone"):
        if selected_zone_entity_ids and zone_state.entity_id not in selected_zone_entity_ids:
            continue

        zone = _state_to_area(zone_state)
        if zone is not None:
            zones.append(zone)

    return zones


async def async_sync_zones(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
) -> tuple[int, int, int]:
    """Synchronize Home Assistant zones to Dawarich."""
    session = async_get_clientsession(hass)
    base_url = get_base_url(entry.data[CONF_HOST], entry.data[CONF_SSL])
    api_key = entry.data[CONF_API_KEY]
    verify_ssl = entry.data[CONF_VERIFY_SSL]
    selected_zone_entity_ids = get_selected_zone_entity_ids(entry)

    zones = collect_home_assistant_zones(hass, selected_zone_entity_ids)
    if not zones:
        _LOGGER.info("No Home Assistant zones found to sync for entry %s", entry.entry_id)
        return 0, 0, 0

    try:
        existing_areas = await async_get_areas(session, base_url, api_key, verify_ssl)
        existing_by_name = {area.name.casefold(): area for area in existing_areas}

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for zone in zones:
            existing_area = existing_by_name.get(zone.name.casefold())
            if existing_area is None:
                await async_create_area(session, base_url, api_key, verify_ssl, zone)
                created_count += 1
                continue

            zone.area_id = existing_area.area_id
            if areas_match(zone, existing_area):
                skipped_count += 1
                continue

            await async_update_area(session, base_url, api_key, verify_ssl, zone)
            updated_count += 1

    except ClientResponseError as err:
        raise HomeAssistantError(
            f"Dawarich zone sync failed with status {err.status}"
        ) from err
    except Exception as err:
        raise HomeAssistantError(f"Dawarich zone sync failed: {err}") from err

    _LOGGER.info(
        "Dawarich zone sync completed: %s created, %s updated, %s unchanged",
        created_count,
        updated_count,
        skipped_count,
    )
    return created_count, updated_count, skipped_count


def is_auto_sync_enabled(entry: config_entries.ConfigEntry) -> bool:
    """Return whether periodic zone sync is enabled."""
    return bool(
        entry.options.get(CONF_AUTO_SYNC_ZONES, entry.data.get(CONF_AUTO_SYNC_ZONES, False))
    )


def _state_to_area(zone_state: State) -> DawarichArea | None:
    latitude = zone_state.attributes.get("latitude")
    longitude = zone_state.attributes.get("longitude")
    radius = zone_state.attributes.get("radius")

    if latitude is None or longitude is None or radius is None:
        return None

    try:
        return DawarichArea(
            name=zone_state.name,
            latitude=float(latitude),
            longitude=float(longitude),
            radius=int(float(radius)),
        )
    except (TypeError, ValueError):
        return None