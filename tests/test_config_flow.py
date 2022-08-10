"""Tests for the seafile component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from typing import Final
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow, setup
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.seafile.const import (
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from custom_components.seafile.exceptions import (
    SeafileConnectionError,
    SeafileRequestError,
)
from tests.setup import (
    MOCK_PASSWORD,
    MOCK_URL,
    MOCK_USERNAME,
    OPTIONS_FLOW_DATA,
    async_mock_client,
)

OPTIONS_FLOW_EDIT_DATA: Final = {
    CONF_PASSWORD: MOCK_PASSWORD,
    CONF_TIMEOUT: 15,
    CONF_SCAN_INTERVAL: 11,
}

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_user(hass: HomeAssistant) -> None:
    """Test user config.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "user"

    with patch(
        "custom_components.seafile.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.seafile.updater.SeafileClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_URL: MOCK_URL,
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )
        await hass.async_block_till_done()

    assert result_configure["flow_id"] == result_init["flow_id"]
    assert result_configure["title"] == MOCK_USERNAME
    assert result_configure["data"][CONF_URL] == MOCK_URL
    assert result_configure["data"][CONF_USERNAME] == MOCK_USERNAME
    assert result_configure["data"][CONF_PASSWORD] == MOCK_PASSWORD
    assert result_configure["data"][CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
    assert result_configure["data"][CONF_TIMEOUT] == DEFAULT_TIMEOUT

    assert len(mock_client.mock_calls) == 3
    assert len(mock_async_setup_entry.mock_calls) == 1


async def test_user_with_request_error(hass: HomeAssistant) -> None:
    """Test user config.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "user"

    with patch(
        "custom_components.seafile.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.seafile.updater.SeafileClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.login = AsyncMock(side_effect=SeafileRequestError)

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_URL: MOCK_URL,
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )
        await hass.async_block_till_done()

    assert result_configure["flow_id"] == result_init["flow_id"]
    assert result_configure["step_id"] == "user"
    assert result_configure["errors"]["base"] == "request.error"

    assert len(mock_client.mock_calls) == 2
    assert len(mock_async_setup_entry.mock_calls) == 0


async def test_user_with_connection_error(hass: HomeAssistant) -> None:
    """Test user config.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "user"

    with patch(
        "custom_components.seafile.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.seafile.updater.SeafileClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.login = AsyncMock(side_effect=SeafileConnectionError)

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_URL: MOCK_URL,
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )
        await hass.async_block_till_done()

    assert result_configure["flow_id"] == result_init["flow_id"]
    assert result_configure["step_id"] == "user"
    assert result_configure["errors"]["base"] == "connection.error"

    assert len(mock_client.mock_calls) == 2
    assert len(mock_async_setup_entry.mock_calls) == 0


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=OPTIONS_FLOW_DATA,
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.seafile.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.seafile.updater.SeafileClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_init["step_id"] == "init"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input=OPTIONS_FLOW_EDIT_DATA,
        )

    assert result_save["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options[CONF_URL] == MOCK_URL
    assert config_entry.options[CONF_USERNAME] == MOCK_USERNAME
    assert config_entry.options[CONF_PASSWORD] == OPTIONS_FLOW_EDIT_DATA[CONF_PASSWORD]
    assert config_entry.options[CONF_TIMEOUT] == OPTIONS_FLOW_EDIT_DATA[CONF_TIMEOUT]
    assert (
        config_entry.options[CONF_SCAN_INTERVAL]
        == OPTIONS_FLOW_EDIT_DATA[CONF_SCAN_INTERVAL]
    )
    assert len(mock_async_setup_entry.mock_calls) == 1


async def test_options_flow_request_error(hass: HomeAssistant) -> None:
    """Test options flow.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=OPTIONS_FLOW_DATA,
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.seafile.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.seafile.updater.SeafileClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.login = AsyncMock(side_effect=SeafileRequestError)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_init["step_id"] == "init"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input=OPTIONS_FLOW_EDIT_DATA,
        )

    assert result_save["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_save["step_id"] == "init"
    assert result_save["errors"]["base"] == "request.error"
    assert len(mock_async_setup_entry.mock_calls) == 1


async def test_options_flow_connection_error(hass: HomeAssistant) -> None:
    """Test options flow.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=OPTIONS_FLOW_DATA,
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.seafile.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.seafile.updater.SeafileClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.login = AsyncMock(side_effect=SeafileConnectionError)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_init["step_id"] == "init"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input=OPTIONS_FLOW_EDIT_DATA,
        )

    assert result_save["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_save["step_id"] == "init"
    assert result_save["errors"]["base"] == "connection.error"
    assert len(mock_async_setup_entry.mock_calls) == 1
