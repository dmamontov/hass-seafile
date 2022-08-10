"""Seafile diagnostic."""

from __future__ import annotations

from typing import Final

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant

from .const import ATTR_AVATAR_URL
from .updater import async_get_updater

TO_REDACT: Final = {
    CONF_TOKEN,
    CONF_URL,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_EMAIL,
    ATTR_AVATAR_URL,
    "contact_email",
    "owner",
    "owner_contact_email",
    "modifier_email",
    "modifier_contact_email",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""

    _data: dict = {"config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT)}

    if _updater := async_get_updater(hass, config_entry.entry_id):
        if hasattr(_updater, "data"):
            _data["data"] = async_redact_data(_updater.data, TO_REDACT)

        if len(_updater.client.diagnostics) > 0:
            _data["requests"] = async_redact_data(
                _updater.client.diagnostics, TO_REDACT
            )

        if hasattr(_updater, "sensors") and _updater.sensors:
            _data["sensors"] = list(_updater.sensors.keys())

    return _data
