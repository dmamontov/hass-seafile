"""General constants."""
from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

# fmt: off
DOMAIN: Final = "seafile"
NAME: Final = "Seafile"
MAINTAINER: Final = "Seafile Ltd."
ATTRIBUTION: Final = "Data provided by Seafile"

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]

THUMBNAIL_SIZE: Final = 256

"""Diagnostic const"""
DIAGNOSTIC_DATE_TIME: Final = "date_time"
DIAGNOSTIC_MESSAGE: Final = "message"
DIAGNOSTIC_CONTENT: Final = "content"

"""Helper const"""
UPDATER: Final = "updater"
UPDATE_LISTENER: Final = "update_listener"
OPTION_IS_FROM_FLOW: Final = "is_from_flow"
SIGNAL_NEW_SENSOR: Final = f"{DOMAIN}-new-sensor"

"""Default settings"""
DEFAULT_SCAN_INTERVAL: Final = 7
DEFAULT_TIMEOUT: Final = 10
DEFAULT_CALL_DELAY: Final = 1
DEFAULT_SLEEP: Final = 3

"""Seafile API client const"""
CLIENT_URL: Final = "{url}/api2"

"""Attributes"""
ATTR_STATE: Final = "state"
ATTR_STATE_NAME: Final = "State"

ATTR_AVATAR_URL: Final = "avatar_url"

ATTR_DEVICE_SW_VERSION: Final = "device_sw_version"

"""Sensors"""
ATTR_REPOSITORIES: Final = "repositories"
ATTR_REPOSITORY_SIZE: Final = "size"
ATTR_REPOSITORY_NAME: Final = "name"
