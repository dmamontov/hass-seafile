"""Tests for the seafile component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
import urllib.parse
from typing import Final
from unittest.mock import AsyncMock

from homeassistant import setup
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    get_fixture_path,
    load_fixture,
)

from custom_components.seafile.const import (
    CLIENT_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    OPTION_IS_FROM_FLOW,
    UPDATER,
)
from custom_components.seafile.helper import get_config_value
from custom_components.seafile.updater import SeafileUpdater

MOCK_URL: Final = "https://seafile.com"
MOCK_USERNAME: Final = "test@seafile.com"
MOCK_PASSWORD: Final = "12345678"

OPTIONS_FLOW_DATA: Final = {
    CONF_URL: MOCK_URL,
    CONF_USERNAME: MOCK_USERNAME,
    CONF_PASSWORD: MOCK_PASSWORD,
    CONF_TIMEOUT: 10,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}

_LOGGER = logging.getLogger(__name__)


async def async_setup(
    hass: HomeAssistant, username: str = MOCK_USERNAME
) -> tuple[SeafileUpdater, MockConfigEntry]:
    """Setup.

    :param hass: HomeAssistant
    :param username: str
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=OPTIONS_FLOW_DATA | {CONF_USERNAME: username},
        options={OPTION_IS_FROM_FLOW: True},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    updater: SeafileUpdater = SeafileUpdater(
        hass,
        get_config_value(config_entry, CONF_URL),
        get_config_value(config_entry, CONF_USERNAME),
        get_config_value(config_entry, CONF_PASSWORD),
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        UPDATER: updater,
    }

    return updater, config_entry


async def async_mock_client(mock_client) -> None:
    """Mock"""

    mock_client.return_value.login = AsyncMock(
        return_value=json.loads(load_fixture("login_data.json"))
    )
    mock_client.return_value.account = AsyncMock(
        return_value=json.loads(load_fixture("account_data.json"))
    )
    mock_client.return_value.server = AsyncMock(
        return_value=json.loads(load_fixture("server_data.json"))
    )
    mock_client.return_value.libraries = AsyncMock(
        return_value=json.loads(load_fixture("libraries_data.json"))
    )

    async def mock_dir(repo_id: str, path: str | None) -> dict:
        """Mock channels"""

        if path == "/My Photos":
            return json.loads(load_fixture("dir_sub_data.json"))

        if path == "/My Photos/Camera":
            return json.loads(load_fixture("dir_sub_sub_data.json"))

        return json.loads(load_fixture("dir_root_data.json"))

    mock_client.return_value.directories = AsyncMock(side_effect=mock_dir)
    mock_client.return_value.file = AsyncMock(
        return_value=load_fixture("file_data.txt")
    )
    mock_client.return_value.thumbnail = AsyncMock(
        return_value=load_image_fixture("thumbnail_data.jpg")
    )


def get_url(
    path: str,
    query_params: dict | None = None,
) -> str:
    """Generate url

    :param path: str
    :param query_params: dict | None
    :return: str
    """

    path += "/"

    if query_params is not None and len(query_params) > 0:
        path += f"?{urllib.parse.urlencode(query_params, doseq=True)}"

    return f"{CLIENT_URL.format(url=MOCK_URL)}/{path}"


def load_image_fixture(filename: str) -> bytes:
    """Load image fixtures"""

    return get_fixture_path(filename, None).read_bytes()


class MultipleSideEffect:  # pylint: disable=too-few-public-methods
    """Multiple side effect"""

    def __init__(self, *fns):
        """init"""

        self.funcs = iter(fns)

    def __call__(self, *args, **kwargs):
        """call"""

        func = next(self.funcs)
        return func(*args, **kwargs)
