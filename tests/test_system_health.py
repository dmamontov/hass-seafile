"""Tests for the seafile component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import get_system_health_info

from custom_components.seafile.const import DOMAIN
from custom_components.seafile.helper import async_get_version
from tests.setup import async_mock_client, async_setup

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_system_health(hass: HomeAssistant) -> None:
    """Test system_health.

    :param hass: HomeAssistant
    """

    with patch("custom_components.seafile.updater.SeafileClient") as mock_client:
        await async_mock_client(mock_client)

        assert await async_setup_component(hass, "system_health", {})
        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        info = await get_system_health_info(hass, DOMAIN)

        assert info is not None

        assert info == {
            "test@seafile.com": "ok",
            "version": "9.0.2",
            "component_version": await async_get_version(hass),
        }
