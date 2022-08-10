"""Tests for the seafile component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT as BINARY_SENSOR_ENTITY_ID_FORMAT,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    load_fixture,
)

from custom_components.seafile.const import (
    ATTR_STATE_NAME,
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


async def test_init(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch("custom_components.seafile.updater.SeafileClient") as mock_client, patch(
        "custom_components.seafile.updater.async_dispatcher_send"
    ):
        await async_mock_client(mock_client)

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater: SeafileUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        state: State = hass.states.get(_generate_id(ATTR_STATE_NAME, updater.username))
        assert state.state == STATE_ON
        assert state.name == ATTR_STATE_NAME
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION


async def test_update_state(hass: HomeAssistant) -> None:
    """Test update state.

    :param hass: HomeAssistant
    """

    with patch("custom_components.seafile.updater.SeafileClient") as mock_client, patch(
        "custom_components.seafile.updater.async_dispatcher_send"
    ):
        await async_mock_client(mock_client)

        def success() -> dict:
            return json.loads(load_fixture("server_data.json"))

        def error() -> None:
            raise SeafileRequestError

        mock_client.return_value.server = AsyncMock(
            side_effect=MultipleSideEffect(success, error)
        )

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: SeafileUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(ATTR_STATE_NAME, updater.username)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.name == ATTR_STATE_NAME
        assert state.attributes["icon"] == "mdi:lan-connect"
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry is not None
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:lan-disconnect"


def _generate_id(code: str, username: str) -> str:
    """Generate unique id

    :param code: str
    :param username: str
    :return str
    """

    return generate_entity_id(
        BINARY_SENSOR_ENTITY_ID_FORMAT,
        username,
        code,
    )
