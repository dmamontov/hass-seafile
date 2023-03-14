"""Sensor component."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_REPOSITORIES, ATTR_STATE, SIGNAL_NEW_SENSOR
from .entity import SeafileEntity
from .updater import SeafileEntityDescription, SeafileUpdater, async_get_updater

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Seafile sensor entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: ConfigEntry object
    :param async_add_entities: AddEntitiesCallback: AddEntitiesCallback callback object
    """

    updater: SeafileUpdater = async_get_updater(hass, config_entry.entry_id)

    @callback
    def add_sensor(entity: SeafileEntityDescription) -> None:
        """Add sensor.

        :param entity: SeafileEntityDescription: Sensor object
        """

        async_add_entities(
            [
                SeafileSensor(
                    f"{config_entry.entry_id}-{entity.description.key}",
                    entity,
                    updater,
                )
            ]
        )

    for sensor in updater.sensors.values():
        add_sensor(sensor)

    updater.new_sensor_callback = async_dispatcher_connect(
        hass, SIGNAL_NEW_SENSOR, add_sensor
    )


# pylint: disable=too-many-ancestors
class SeafileSensor(SeafileEntity, SensorEntity):
    """Seafile sensor entry."""

    def __init__(
        self,
        unique_id: str,
        entity: SeafileEntityDescription,
        updater: SeafileUpdater,
    ) -> None:
        """Initialize sensor.

        :param unique_id: str: Unique ID
        :param entity: SeafileEntityDescription object
        :param updater: SeafileUpdater: Seafile updater object
        """

        SeafileEntity.__init__(
            self, unique_id, entity.description, updater, ENTITY_ID_FORMAT
        )

        self._attr_repository_code = entity.repository_code
        self._attr_custom_key = entity.custom_key

        if self._attr_repository_code is not None:
            self._attr_native_value = (
                self._updater.data.get(ATTR_REPOSITORIES, {})
                .get(self._attr_repository_code, {})
                .get(self._attr_custom_key, None)
            )
        else:
            self._attr_native_value = self._updater.data.get(
                entity.description.key, None
            )

        self._attr_device_info = entity.device_info

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        is_available: bool = self._updater.data.get(ATTR_STATE, False)

        state: Any = None

        if self._attr_repository_code is not None:
            state = (
                self._updater.data.get(ATTR_REPOSITORIES, {})
                .get(self._attr_repository_code, {})
                .get(self._attr_custom_key, None)
            )
        else:
            state = self._updater.data.get(self.entity_description.key, None)

        if (
            self._attr_native_value == state
            and self._attr_available == is_available  # type: ignore
        ):
            return

        self._attr_available = is_available
        self._attr_native_value = state

        self.async_write_ha_state()
