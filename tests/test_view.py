"""Tests for the seafile component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,line-too-long

from __future__ import annotations

import logging
from datetime import timedelta
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientResponse
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import get_url
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.seafile.const import DEFAULT_SCAN_INTERVAL, THUMBNAIL_SIZE
from custom_components.seafile.exceptions import SeafileConnectionError
from custom_components.seafile.views import async_generate_thumbnail_url
from tests.setup import async_mock_client, async_setup, load_image_fixture

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_thumbnail(hass: HomeAssistant, hass_client: mock_aiohttp_client) -> None:
    """Test thumbnail.

    :param hass: HomeAssistant
    :param hass_client: mock_aiohttp_client
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

        url: str = async_generate_thumbnail_url(
            get_url(hass),
            config_entry.entry_id,
            "704f23aa-e086-40a3-977e-7a07c798971d",
            "test.jpg",
            THUMBNAIL_SIZE,
        )

        http_client = await hass_client()
        response = cast(
            ClientResponse, await http_client.get(url.replace(get_url(hass), ""))
        )

        assert response.status == 200
        assert await response.content.read() == load_image_fixture("thumbnail_data.jpg")
        assert response.content_type == "image/jpeg"


async def test_thumbnail_with_path(
    hass: HomeAssistant, hass_client: mock_aiohttp_client
) -> None:
    """Test thumbnail.

    :param hass: HomeAssistant
    :param hass_client: mock_aiohttp_client
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

        url: str = async_generate_thumbnail_url(
            get_url(hass),
            config_entry.entry_id,
            "704f23aa-e086-40a3-977e-7a07c798971d",
            "images/test.jpg",
            THUMBNAIL_SIZE,
        )

        http_client = await hass_client()
        response = cast(
            ClientResponse, await http_client.get(url.replace(get_url(hass), ""))
        )

        assert response.status == 200
        assert await response.content.read() == load_image_fixture("thumbnail_data.jpg")
        assert response.content_type == "image/jpeg"


async def test_thumbnail_with_converted_heic(
    hass: HomeAssistant, hass_client: mock_aiohttp_client
) -> None:
    """Test thumbnail.

    :param hass: HomeAssistant
    :param hass_client: mock_aiohttp_client
    """

    with patch("custom_components.seafile.updater.SeafileClient") as mock_client, patch(
        "custom_components.seafile.updater.async_dispatcher_send"
    ):
        await async_mock_client(mock_client)

        mock_client.return_value.file = AsyncMock(
            return_value=load_image_fixture("converted.heic")
        )

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        url: str = async_generate_thumbnail_url(
            get_url(hass),
            config_entry.entry_id,
            "704f23aa-e086-40a3-977e-7a07c798971d",
            "images/test.heic",
            THUMBNAIL_SIZE,
        )

        http_client = await hass_client()
        response = cast(
            ClientResponse, await http_client.get(url.replace(get_url(hass), ""))
        )

        assert response.status == 200
        assert response.content_type == "image/jpeg"


async def test_thumbnail_error(
    hass: HomeAssistant, hass_client: mock_aiohttp_client
) -> None:
    """Test thumbnail error.

    :param hass: HomeAssistant
    :param hass_client: mock_aiohttp_client
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

        url: str = async_generate_thumbnail_url(
            get_url(hass),
            "error",
            "704f23aa-e086-40a3-977e-7a07c798971d",
            "test.jpg",
            THUMBNAIL_SIZE,
        )

        http_client = await hass_client()
        response = cast(
            ClientResponse, await http_client.get(url.replace(get_url(hass), ""))
        )

        assert response.status == 404
        assert await response.content.read() == b"Unable to find entry with id: error"

        url = async_generate_thumbnail_url(
            get_url(hass),
            config_entry.entry_id,
            "error",
            "test.jpg",
            THUMBNAIL_SIZE,
        )

        http_client = await hass_client()
        response = cast(
            ClientResponse, await http_client.get(url.replace(get_url(hass), ""))
        )

        assert response.status == 404
        assert await response.content.read() == b"Unable to find library with id: error"


async def test_thumbnail_api_error(
    hass: HomeAssistant, hass_client: mock_aiohttp_client
) -> None:
    """Test thumbnail api error.

    :param hass: HomeAssistant
    :param hass_client: mock_aiohttp_client
    """

    with patch("custom_components.seafile.updater.SeafileClient") as mock_client, patch(
        "custom_components.seafile.updater.async_dispatcher_send"
    ):
        await async_mock_client(mock_client)

        mock_client.return_value.thumbnail = AsyncMock(
            side_effect=SeafileConnectionError
        )

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        url: str = async_generate_thumbnail_url(
            get_url(hass),
            config_entry.entry_id,
            "704f23aa-e086-40a3-977e-7a07c798971d",
            "test.jpg",
            THUMBNAIL_SIZE,
        )

        http_client = await hass_client()
        response = cast(
            ClientResponse, await http_client.get(url.replace(get_url(hass), ""))
        )

        assert response.status == 404
        assert await response.content.read() == b"Thumbnail not found"
