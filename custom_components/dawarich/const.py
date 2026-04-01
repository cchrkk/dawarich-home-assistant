"""Constants for the Dawarich integration."""

from datetime import timedelta
from enum import Enum

DOMAIN = "dawarich"


DEFAULT_PORT = 80
DEFAULT_NAME = "Dawarich"
DEFAULT_SSL = False
DEFAULT_VERIFY_SSL = True
CONF_DEVICE = "mobile_app"
CONF_AUTO_SYNC_ZONES = "auto_sync_zones"
CONF_SYNC_ZONE_INTERVAL = "sync_zone_interval"
CONF_SYNC_ZONES = "sync_zones"
DEFAULT_AUTO_SYNC_ZONES = False
DEFAULT_SYNC_ZONE_INTERVAL = 24
UPDATE_INTERVAL = timedelta(seconds=60)
VERSION_UPDATE_INTERVAL = timedelta(hours=1)


class DawarichTrackerStates(Enum):
    """States of the Dawarich tracker sensor."""

    UNKNOWN = "unknown"
    SUCCESS = "success"
    ERROR = "error"
