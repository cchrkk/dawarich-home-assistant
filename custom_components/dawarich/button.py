"""Button platform for the Dawarich integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.dawarich import DawarichConfigEntry

from .const import DOMAIN
from .zone_sync import async_sync_zones

_LOGGER = logging.getLogger(__name__)

SYNC_ZONES_BUTTON = ButtonEntityDescription(
    key="sync_zones",
    name="Sync Home Assistant Zones",
    icon="mdi:map-marker-sync",
    translation_key="sync_zones",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DawarichConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dawarich button entities."""
    entry_id = entry.entry_id
    name = entry.data[CONF_NAME]
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=name,
        manufacturer="Dawarich",
        configuration_url=entry.runtime_data.api.url,
    )

    async_add_entities(
        [
            DawarichSyncZonesButton(
                entry=entry,
                description=SYNC_ZONES_BUTTON,
                device_info=device_info,
            )
        ]
    )


class DawarichSyncZonesButton(ButtonEntity):
    """Button used to synchronize Home Assistant zones to Dawarich."""

    entity_description = SYNC_ZONES_BUTTON

    def __init__(
        self,
        entry: DawarichConfigEntry,
        description: ButtonEntityDescription,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the button."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}/{description.key}"
        self._attr_device_info = device_info
        self.entity_description = description

    async def async_press(self) -> None:
        """Synchronize zones from Home Assistant to Dawarich."""
        await async_sync_zones(self.hass, self._entry)