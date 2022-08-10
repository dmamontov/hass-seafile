"""Tests for the seafile component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,line-too-long

from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components import media_source
from homeassistant.components.media_source import const
from homeassistant.components.media_source.error import MediaSourceError, Unresolvable
from homeassistant.components.media_source.models import BrowseMediaSource, PlayMedia
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import get_url
from homeassistant.setup import async_setup_component
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    load_fixture,
)

from custom_components.seafile.const import DEFAULT_SCAN_INTERVAL, DOMAIN
from custom_components.seafile.exceptions import SeafileConnectionError
from tests.setup import MOCK_URL, MOCK_USERNAME, async_mock_client, async_setup

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.fixture(autouse=True)
async def setup_media_source(hass) -> None:
    """Set up media source."""
    assert await async_setup_component(hass, "media_source", {})


async def test_media_source(hass: HomeAssistant) -> None:
    """Test media source.

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

        media: BrowseMediaSource = await media_source.async_browse_media(
            hass,
            f"{const.URI_SCHEME}{DOMAIN}",
        )

        assert media.as_dict() == {
            "can_expand": True,
            "can_play": False,
            "children": [
                {
                    "can_expand": True,
                    "can_play": False,
                    "children_media_class": "directory",
                    "media_class": "app",
                    "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}",
                    "media_content_type": "",
                    "thumbnail": f"{MOCK_URL}/media/avatars/e/1/d853b3eb9e2d392f9a71139a5cd55c/resized/72/224b3d851f5a992def212ebb2dd6935f.png",
                    "title": MOCK_USERNAME,
                }
            ],
            "children_media_class": "app",
            "media_class": "app",
            "media_content_id": "media-source://seafile",
            "media_content_type": "",
            "not_shown": 0,
            "thumbnail": None,
            "title": "Seafile",
        }

        media = await media_source.async_browse_media(
            hass,
            f"{const.URI_SCHEME}{DOMAIN}/{config_entry.entry_id}",
        )

        assert media.as_dict() == {
            "can_expand": True,
            "can_play": False,
            "children": [
                {
                    "can_expand": True,
                    "can_play": False,
                    "children_media_class": "directory",
                    "media_class": "directory",
                    "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d",
                    "media_content_type": "",
                    "thumbnail": None,
                    "title": "Camera",
                },
                {
                    "can_expand": True,
                    "can_play": False,
                    "children_media_class": "directory",
                    "media_class": "directory",
                    "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}/039e494b-2f2b-4716-940d-beecc654c8c8",
                    "media_content_type": "",
                    "thumbnail": None,
                    "title": "Documents",
                },
            ],
            "children_media_class": "directory",
            "media_class": "app",
            "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}",
            "media_content_type": "",
            "not_shown": 0,
            "thumbnail": f"{MOCK_URL}/media/avatars/e/1/d853b3eb9e2d392f9a71139a5cd55c/resized/72/224b3d851f5a992def212ebb2dd6935f.png",
            "title": MOCK_USERNAME,
        }

        media = await media_source.async_browse_media(
            hass,
            f"{const.URI_SCHEME}{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d",
        )

        assert media.as_dict() == {
            "can_expand": True,
            "can_play": False,
            "children": [
                {
                    "can_expand": True,
                    "can_play": False,
                    "children_media_class": "directory",
                    "media_class": "directory",
                    "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/My "
                    "Photos",
                    "media_content_type": "",
                    "thumbnail": None,
                    "title": "My Photos",
                },
                {
                    "can_expand": False,
                    "can_play": True,
                    "children_media_class": None,
                    "media_class": "image",
                    "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/test.jpg",
                    "media_content_type": "image",
                    "thumbnail": f"{get_url(hass)}/api/{DOMAIN}/thumbnail/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/256/test.jpg",
                    "title": "test.jpg",
                },
            ],
            "children_media_class": "directory",
            "media_class": "directory",
            "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d",
            "media_content_type": "",
            "not_shown": 0,
            "thumbnail": None,
            "title": "Camera",
        }

        media = await media_source.async_browse_media(
            hass,
            f"{const.URI_SCHEME}{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/My Photos",
        )

        assert media.as_dict() == {
            "can_expand": True,
            "can_play": False,
            "children": [
                {
                    "can_expand": True,
                    "can_play": False,
                    "children_media_class": "directory",
                    "media_class": "directory",
                    "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/My "
                    "Photos/Camera",
                    "media_content_type": "",
                    "thumbnail": None,
                    "title": "Camera",
                }
            ],
            "children_media_class": "directory",
            "media_class": "directory",
            "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/My "
            "Photos/My Photos",
            "media_content_type": "",
            "not_shown": 0,
            "thumbnail": None,
            "title": "My Photos",
        }

        media = await media_source.async_browse_media(
            hass,
            f"{const.URI_SCHEME}{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/My Photos/Camera",
        )

        assert media.as_dict() == {
            "can_expand": True,
            "can_play": False,
            "children": [
                {
                    "can_expand": False,
                    "can_play": True,
                    "children_media_class": None,
                    "media_class": "video",
                    "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/My "
                    "Photos/Camera/test.flv",
                    "media_content_type": "video",
                    "thumbnail": None,
                    "title": "test.flv",
                }
            ],
            "children_media_class": "directory",
            "media_class": "directory",
            "media_content_id": f"media-source://{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/My "
            "Photos/Camera/Camera",
            "media_content_type": "",
            "not_shown": 0,
            "thumbnail": None,
            "title": "Camera",
        }


async def test_media_source_entry_error(hass: HomeAssistant) -> None:
    """Test media source entry error.

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

        with pytest.raises(MediaSourceError) as error:
            await media_source.async_browse_media(
                hass,
                f"{const.URI_SCHEME}{DOMAIN}/error",
            )

        assert str(error.value) == "Unable to find entry with id: error"


async def test_media_source_uuid_error(hass: HomeAssistant) -> None:
    """Test media source uuid error.

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

        with pytest.raises(MediaSourceError) as error:
            await media_source.async_browse_media(
                hass,
                f"{const.URI_SCHEME}{DOMAIN}/{config_entry.entry_id}/error",
            )

        assert str(error.value) == "Unable to find library with id: error"


async def test_media_source_updater_error(hass: HomeAssistant) -> None:
    """Test media source updater error.

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

        with pytest.raises(MediaSourceError) as error:
            await media_source.async_browse_media(
                hass,
                f"{const.URI_SCHEME}{DOMAIN}/error/704f23aa-e086-40a3-977e-7a07c798971d",
            )

        assert str(error.value) == "Unable to find entry with id: error"


async def test_media_source_directories_error(hass: HomeAssistant) -> None:
    """Test media source directories error.

    :param hass: HomeAssistant
    """

    with patch("custom_components.seafile.updater.SeafileClient") as mock_client, patch(
        "custom_components.seafile.updater.async_dispatcher_send"
    ):
        await async_mock_client(mock_client)
        mock_client.return_value.directories = AsyncMock(
            side_effect=SeafileConnectionError
        )

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        with pytest.raises(MediaSourceError) as error:
            await media_source.async_browse_media(
                hass,
                f"{const.URI_SCHEME}{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d",
            )

        assert str(error.value) == "Unable to find path: /"


async def test_media_source_play(hass: HomeAssistant) -> None:
    """Test media source play.

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

        media = await media_source.async_resolve_media(
            hass,
            f"{const.URI_SCHEME}{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/test.jpg",
            None,
        )
        assert media == PlayMedia(
            url=load_fixture("file_data.txt").strip('"'), mime_type="image/jpeg"
        )


async def test_media_source_play_uuid_error(hass: HomeAssistant) -> None:
    """Test media source play uuid error.

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

        with pytest.raises(Unresolvable) as error:
            await media_source.async_resolve_media(
                hass,
                f"{const.URI_SCHEME}{DOMAIN}/{config_entry.entry_id}/error/test.jpg",
                None,
            )

        assert str(error.value) == "Unable to find library with id: error"


async def test_media_source_play_entry_error(hass: HomeAssistant) -> None:
    """Test media source play entry error.

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

        with pytest.raises(Unresolvable) as error:
            await media_source.async_resolve_media(
                hass,
                f"{const.URI_SCHEME}{DOMAIN}/error/704f23aa-e086-40a3-977e-7a07c798971d/test.jpg",
                None,
            )

        assert str(error.value) == "Unable to find entry with id: error"


async def test_media_source_play_url_error(hass: HomeAssistant) -> None:
    """Test media source play url error.

    :param hass: HomeAssistant
    """

    with patch("custom_components.seafile.updater.SeafileClient") as mock_client, patch(
        "custom_components.seafile.updater.async_dispatcher_send"
    ):
        await async_mock_client(mock_client)

        mock_client.return_value.file = AsyncMock(side_effect=SeafileConnectionError)

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        with pytest.raises(Unresolvable) as error:
            await media_source.async_resolve_media(
                hass,
                f"{const.URI_SCHEME}{DOMAIN}/{config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/test.jpg",
                None,
            )

        assert (
            str(error.value)
            == f"Could not resolve media item: {config_entry.entry_id}/704f23aa-e086-40a3-977e-7a07c798971d/test.jpg"
        )
