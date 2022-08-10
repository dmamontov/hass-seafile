"""Integration helper."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus, unquote_plus
from uuid import UUID

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.util import slugify
from httpx import codes

from .const import DEFAULT_TIMEOUT, DOMAIN
from .updater import SeafileUpdater

_LOGGER = logging.getLogger(__name__)


def get_config_value(
    config_entry: config_entries.ConfigEntry | None, param: str, default=None
) -> Any:
    """Get current value for configuration parameter.

    :param config_entry: config_entries.ConfigEntry|None: config entry from Flow
    :param param: str: parameter name for getting value
    :param default: default value for parameter, defaults to None
    :return Any: parameter value, or default value or None
    """

    return (
        config_entry.options.get(param, config_entry.data.get(param, default))
        if config_entry is not None
        else default
    )


async def async_verify_access(  # pylint: disable=too-many-arguments
    hass: HomeAssistant,
    url: str,
    username: str,
    password: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> codes:
    """Verify authentication data.

    :param hass: HomeAssistant: Home Assistant object
    :param url: str: URL
    :param username: str: Basic auth username
    :param password: str: Basic auth password
    :param timeout: int: Timeout
    :return int: last update success
    """

    updater = SeafileUpdater(
        hass=hass,
        url=url,
        username=username,
        password=password,
        timeout=timeout,
        is_only_check=True,
    )

    await updater.async_request_refresh()
    await updater.async_stop()

    return updater.code


async def async_get_version(hass: HomeAssistant) -> str:
    """Get the documentation url for creating a local user.

    :param hass: HomeAssistant: Home Assistant object
    :return str: Documentation URL
    """

    integration = await async_get_integration(hass, DOMAIN)

    return f"{integration.version}"


def generate_entity_id(
    entity_id_format: str, username: str, name: str | None = None
) -> str:
    """Generate Entity ID

    :param entity_id_format: str: Format
    :param username: str: Username
    :param name: str | None: Name
    :return str: Entity ID
    """

    _name: str = f"_{name}" if name is not None else ""

    return entity_id_format.format(slugify(f"{DOMAIN}_{username}{_name}".lower()))


def is_valid_uuid(uuid: str, version: int = 4) -> bool:
    """Check if uuid is a valid UUID.

    :param uuid: str
    :param version: int
    :return bool
    """

    try:
        uuid_object = UUID(uuid, version=version)
    except ValueError:
        return False

    return str(uuid_object) == uuid


def get_short_mime(mime: str | None) -> str | None:
    """Get short mime

    :param mime: str | None
    :return str | None
    """

    if mime is None:
        return None

    path: list = mime.split("/")

    return path[0]


def encode_path(path: str) -> str:
    """Encode path

    :param path: str
    :return str
    """

    # Parentheses must be removed, they break the link in css
    for chars in (("(", "|28|"), (")", "|29|")):
        path = path.replace(*chars)

    return quote_plus(path, "/").strip("/")


def decode_path(path: str) -> str:
    """Decode path

    :param path: str
    :return str
    """

    path = unquote_plus(path)

    for chars in (("|28|", "("), ("|29|", ")")):
        path = path.replace(*chars)

    return path
