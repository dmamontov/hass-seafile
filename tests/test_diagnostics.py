"""Tests for the seafile component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging

import pytest
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import load_fixture
from pytest_httpx import HTTPXMock

from custom_components.seafile.const import DOMAIN, UPDATER
from custom_components.seafile.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)
from custom_components.seafile.updater import SeafileUpdater
from tests.setup import async_setup, get_url

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
async def test_init(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("account_data.json"),
        method="GET",
        url=get_url("account/info"),
    )
    httpx_mock.add_response(
        text=load_fixture("libraries_data.json"),
        method="GET",
        url=get_url("repos", {"type": "mine"}),
    )
    httpx_mock.add_response(
        text=load_fixture("server_data.json"), method="GET", url=get_url("server-info")
    )

    _, config_entry = await async_setup(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    updater: SeafileUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

    assert updater.last_update_success

    diagnostics_data: dict = await async_get_config_entry_diagnostics(
        hass, config_entry
    )

    assert diagnostics_data["config_entry"] == async_redact_data(
        config_entry.as_dict(), TO_REDACT
    )
    assert diagnostics_data["data"] == async_redact_data(updater.data, TO_REDACT)
    assert diagnostics_data["requests"] == async_redact_data(
        updater.client.diagnostics, TO_REDACT
    )
    assert diagnostics_data["sensors"] == [
        "space_usage",
        "704f23aa-e086-40a3-977e-7a07c798971d_used",
        "039e494b-2f2b-4716-940d-beecc654c8c8_used",
    ]
