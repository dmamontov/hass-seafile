"""Tests for the seafile component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.sensor import ENTITY_ID_FORMAT as SENSOR_ENTITY_ID_FORMAT
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    load_fixture,
)

from custom_components.seafile.const import (
    ATTRIBUTION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    UPDATER,
)
from custom_components.seafile.exceptions import SeafileRequestError
from custom_components.seafile.helper import generate_entity_id
from custom_components.seafile.updater import SeafileUpdater
from tests.setup import MultipleSideEffect, async_mock_client, async_setup

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_update_sensors(hass: HomeAssistant) -> None:
    """Test update sensors.

    :param hass: HomeAssistant
    """

    with patch("custom_components.seafile.updater.SeafileClient") as mock_client:
        await async_mock_client(mock_client)

        def success() -> dict:
            return json.loads(load_fixture("server_data.json"))

        def error() -> None:
            raise SeafileRequestError

        mock_client.return_value.server = AsyncMock(
            side_effect=MultipleSideEffect(success, success, success, error)
        )

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: SeafileUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 30)
        )
        await hass.async_block_till_done()

        unique_id: str = _generate_id("space_total", updater.username)
        entry = registry.async_get(unique_id)

        assert hass.states.get(unique_id) is None
        assert entry is None

        state = hass.states.get(_generate_id("space_usage", updater.username))
        assert state.state == str(81802066434)
        assert state.name == "Space usage"
        assert state.attributes["icon"] == "mdi:harddisk"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(
            _generate_id("704f23aa-e086-40a3-977e-7a07c798971d_used", updater.username)
        )
        assert state.state == str(74256142158)
        assert state.name == "Camera used"
        assert state.attributes["icon"] == "mdi:harddisk"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(
            _generate_id("039e494b-2f2b-4716-940d-beecc654c8c8_used", updater.username)
        )
        assert state.state == str(7545924276)
        assert state.name == "Documents used"
        assert state.attributes["icon"] == "mdi:harddisk"
        assert state.attributes["attribution"] == ATTRIBUTION

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(_generate_id("space_usage", updater.username))
        assert state.state == STATE_UNAVAILABLE

        state = hass.states.get(
            _generate_id("704f23aa-e086-40a3-977e-7a07c798971d_used", updater.username)
        )
        assert state.state == STATE_UNAVAILABLE

        state = hass.states.get(
            _generate_id("039e494b-2f2b-4716-940d-beecc654c8c8_used", updater.username)
        )
        assert state.state == STATE_UNAVAILABLE


async def test_update_new_sensors(hass: HomeAssistant) -> None:
    """Test update new sensors.

    :param hass: HomeAssistant
    """

    with patch("custom_components.seafile.updater.SeafileClient") as mock_client:
        await async_mock_client(mock_client)

        def success() -> dict:
            return json.loads(load_fixture("libraries_data.json"))

        def success_two() -> dict:
            return json.loads(load_fixture("libraries_change_data.json"))

        mock_client.return_value.libraries = AsyncMock(
            side_effect=MultipleSideEffect(success, success_two)
        )

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: SeafileUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(
            "999e494b-2f2b-4716-940d-beecc654c8c8_used", updater.username
        )
        entry: er.RegistryEntry | None = registry.async_get(unique_id)

        assert hass.states.get(unique_id) is None
        assert entry is None

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 30)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == str(7745924276)
        assert state.name == "New used"
        assert state.attributes["icon"] == "mdi:harddisk"
        assert state.attributes["attribution"] == ATTRIBUTION


def _generate_id(code: str, username: str) -> str:
    """Generate unique id

    :param code: str
    :param username: str
    :return str
    """

    return generate_entity_id(
        SENSOR_ENTITY_ID_FORMAT,
        username,
        code,
    )
