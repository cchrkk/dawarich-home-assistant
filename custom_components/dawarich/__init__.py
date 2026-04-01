"""The Dawarich integration."""

import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from dawarich_api import DawarichAPI
from homeassistant import config_entries
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SSL,
    CONF_VERIFY_SSL,
    MAJOR_VERSION,
    Platform,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DEVICE,
    CONF_SYNC_ZONE_INTERVAL,
    DEFAULT_SYNC_ZONE_INTERVAL,
    DOMAIN,
)
from .coordinator import DawarichStatsCoordinator, DawarichVersionCoordinator
from .helpers import get_api
from .zone_sync import async_sync_zones, is_auto_sync_enabled

VERSION = json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

_LOGGER = logging.getLogger(__name__)

type DawarichConfigEntry = config_entries.ConfigEntry[DawarichConfigEntryData]


@dataclass
class DawarichConfigEntryData:
    """Runtime data definitions."""

    api: DawarichAPI
    coordinator: DawarichStatsCoordinator
    version_coordinator: DawarichVersionCoordinator
    zone_sync_unsub: CALLBACK_TYPE | None = None
    options_unsub: CALLBACK_TYPE | None = None


async def async_setup_entry(hass: HomeAssistant, entry: DawarichConfigEntry) -> bool:
    """Set up Dawarich from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    host = entry.data[CONF_HOST]
    api_key = entry.data[CONF_API_KEY]
    use_ssl = entry.data[CONF_SSL]
    verify_ssl = entry.data[CONF_VERIFY_SSL]

    api = get_api(host, api_key, use_ssl, verify_ssl)

    if MAJOR_VERSION < 2025:
        _LOGGER.warning(
            "You are using a deprecated version of home assistant for Dawarich. In version 0.8.0 of"
            " dawarich-home-assistantyou will need at least Home Assistant Core version 2025.1"
        )

    coordinator = DawarichStatsCoordinator(hass, api, entry.entry_id)
    await coordinator.async_config_entry_first_refresh()
    version_coordinator = DawarichVersionCoordinator(hass, api, entry.entry_id)
    await version_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = DawarichConfigEntryData(
        api=api, coordinator=coordinator, version_coordinator=version_coordinator
    )
    entry.runtime_data.options_unsub = entry.add_update_listener(_async_update_listener)

    if is_auto_sync_enabled(entry):
        interval_hours = int(
            entry.options.get(
                CONF_SYNC_ZONE_INTERVAL,
                entry.data.get(CONF_SYNC_ZONE_INTERVAL, DEFAULT_SYNC_ZONE_INTERVAL),
            )
        )

        async def _async_sync_zones_periodically(_: Any) -> None:
            await async_sync_zones(hass, entry)

        entry.runtime_data.zone_sync_unsub = async_track_time_interval(
            hass,
            _async_sync_zones_periodically,
            timedelta(hours=interval_hours),
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        if entry.runtime_data.zone_sync_unsub is not None:
            entry.runtime_data.zone_sync_unsub()
        if entry.runtime_data.options_unsub is not None:
            entry.runtime_data.options_unsub()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


# Migration from 1 to 2
async def async_migrate_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Migrate an old entry."""
    if entry.version > 1:
        # Downgrade not supported
        return False

    if entry.version == 1:
        data = {}
        data[CONF_HOST] = (
            entry.data["url"]
            .removeprefix("https://")
            .removeprefix("http://")
            .split(":")[0]
        )
        try:
            data[CONF_PORT] = (
                entry.data["url"]
                .removeprefix("https://")
                .removeprefix("http://")
                .split(":")[1]
            )
        except IndexError:
            data[CONF_PORT] = 80 if entry.data["url"].startswith("http") else 443
        data[CONF_SSL] = entry.data["url"].startswith("https")
        data[CONF_API_KEY] = entry.data["api_key"]
        data[CONF_NAME] = entry.data["friendly_name"]
        data[CONF_VERIFY_SSL] = False
        data[CONF_DEVICE] = entry.data.get("mobile_app", None)

        hass.config_entries.async_update_entry(entry, data=data, version=2)

    _LOGGER.info("Migrated %s to config flow version %s", entry.entry_id, entry.version)
    return True
