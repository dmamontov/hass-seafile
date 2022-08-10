"""Provide info to system health."""

from __future__ import annotations

import logging

from homeassistant.components.system_health import SystemHealthRegistration
from homeassistant.core import HomeAssistant, callback

from .const import ATTR_DEVICE_SW_VERSION, ATTR_STATE, DOMAIN, UPDATER
from .helper import async_get_version
from .updater import SeafileUpdater

_LOGGER = logging.getLogger(__name__)


@callback
def async_register(hass: HomeAssistant, register: SystemHealthRegistration) -> None:
    """Register system health info

    :param hass: HomeAssistant
    :param register: SystemHealthRegistration
    """

    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, str]:
    """System health info

    :param hass: HomeAssistant
    :return dict[str, Any]
    """

    info: dict[str, str] = {
        "component_version": f"{await async_get_version(hass)}",
        "version": "",
    }

    for integration in hass.data[DOMAIN].values():
        updater: SeafileUpdater = integration[UPDATER]

        if len(info["version"]) == 0:
            info["version"] = updater.data.get(ATTR_DEVICE_SW_VERSION, "")

        info[updater.username] = (
            "ok" if updater.data.get(ATTR_STATE, False) else "unreachable"
        )

    return info
