"""Seafile data updater."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from typing import Any, Final

from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass
from homeassistant.const import DATA_BYTES
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import event
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import (
    DeviceEntryType,
    DeviceInfo,
    EntityCategory,
    EntityDescription,
)
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import utcnow
from httpx import codes

from .client import SeafileClient
from .const import (
    ATTR_AVATAR_URL,
    ATTR_DEVICE_SW_VERSION,
    ATTR_REPOSITORIES,
    ATTR_REPOSITORY_NAME,
    ATTR_REPOSITORY_SIZE,
    ATTR_STATE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAINTAINER,
    NAME,
    SIGNAL_NEW_SENSOR,
    UPDATER,
)
from .exceptions import SeafileConnectionError, SeafileError, SeafileRequestError

PREPARE_METHODS: Final = (
    "server",
    "account",
    "libraries",
)

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-branches,too-many-lines,too-many-arguments
class SeafileUpdater(DataUpdateCoordinator):
    """Seafile data updater for interaction with Seafile API."""

    client: SeafileClient
    code: codes = codes.BAD_GATEWAY

    url: str
    username: str

    new_sensor_callback: CALLBACK_TYPE | None = None

    _scan_interval: int
    _is_only_check: bool = False
    _is_reauthorization: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        username: str,
        password: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        timeout: int = DEFAULT_TIMEOUT,
        is_only_check: bool = False,
    ) -> None:
        """Initialize updater.

        :rtype: object
        :param hass: HomeAssistant: Home Assistant object
        :param url: str: URL
        :param username: str: Username
        :param password: str: Password
        :param scan_interval: int: Update interval
        :param timeout: int: Query execution timeout
        :param is_only_check: bool: Only config flow
        """

        url = url.removesuffix("/")

        self.client = SeafileClient(
            get_async_client(hass, False),
            url,
            username,
            password,
            timeout,
        )

        self.username = username
        self.url = url

        self._scan_interval = scan_interval
        self._is_only_check = is_only_check

        if hass is not None:
            super().__init__(
                hass,
                _LOGGER,
                name=f"{NAME} updater",
                update_interval=self._update_interval,
                update_method=self.update,
            )

        self.data: dict[str, Any] = {ATTR_REPOSITORIES: {}}

        self.sensors: dict[str, SeafileEntityDescription] = {}

        self._is_first_update: bool = True

    async def async_stop(self) -> None:
        """Stop updater"""

        if self.new_sensor_callback is not None:
            self.new_sensor_callback()  # pylint: disable=not-callable

    @cached_property
    def _update_interval(self) -> timedelta:
        """Update interval

        :return timedelta: update_interval
        """

        return timedelta(seconds=self._scan_interval)

    async def update(self) -> dict:
        """Update Seafile information.

        :return dict: dict with Seafile data.
        """

        self.code = codes.OK

        _err: SeafileError | None = None

        try:
            if self._is_reauthorization or self._is_first_update:
                await self.client.login()

            for method in PREPARE_METHODS:
                if not self._is_only_check or method == "server":
                    await self._async_prepare(method, self.data)
        except SeafileConnectionError as _e:
            _err = _e

            self._is_reauthorization = True
            self.code = codes.NOT_FOUND
        except SeafileRequestError as _e:
            _err = _e

            self._is_reauthorization = True
            self.code = codes.FORBIDDEN
        else:
            self._is_reauthorization = False

            if self._is_first_update:
                self._is_first_update = False

        self.data[ATTR_STATE] = codes.is_success(self.code)

        return self.data

    @property
    def device_info(self) -> DeviceInfo:
        """Device info.

        :return DeviceInfo: Service DeviceInfo.
        """

        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self.username)},
            name=self.username,
            manufacturer=MAINTAINER,
            sw_version=self.data.get(ATTR_DEVICE_SW_VERSION, None),
            configuration_url=self.url,
        )

    def schedule_refresh(self, offset: timedelta) -> None:
        """Schedule refresh.

        :param offset: timedelta
        """

        if self._unsub_refresh:  # type: ignore
            self._unsub_refresh()  # type: ignore
            self._unsub_refresh = None

        self._unsub_refresh = event.async_track_point_in_utc_time(
            self.hass,
            self._job,
            utcnow().replace(microsecond=0) + offset,
        )

    async def _async_prepare(self, method: str, data: dict) -> None:
        """Prepare data.

        :param method: str
        :param data: dict
        """

        action = getattr(self, f"_async_prepare_{method}")

        if action is not None:
            await action(data)

    async def _async_prepare_server(self, data: dict) -> None:
        """Prepare server.

        :param data: dict
        """

        response: dict = await self.client.server()

        if "version" in response:
            data[ATTR_DEVICE_SW_VERSION] = response["version"]

    async def _async_prepare_account(self, data: dict) -> None:
        """Prepare account.

        :param data: dict
        """

        response: dict = await self.client.account()

        if ATTR_AVATAR_URL in response:
            data[ATTR_AVATAR_URL] = response[ATTR_AVATAR_URL]

        for code in ("total", "usage"):
            if code in response and int(response[code]) >= 0:
                _code: str = f"space_{code}"

                data[_code] = int(response[code])

                self._add_size_sensor(_code, f"Space {code}", EntityCategory.DIAGNOSTIC)

    async def _async_prepare_libraries(self, data: dict) -> None:
        """Prepare libraries.

        :param data: dict
        """

        response: list = await self.client.libraries()

        for lib in response:
            data[ATTR_REPOSITORIES][lib["id"]] = {
                ATTR_REPOSITORY_SIZE: lib["size"],
                ATTR_REPOSITORY_NAME: lib["name"],
            }

            self._add_size_sensor(
                f"{lib['id']}_used",
                f"{lib['name']} used",
                repository_code=lib["id"],
                custom_key=ATTR_REPOSITORY_SIZE,
            )

    def _add_size_sensor(
        self,
        code: str,
        name: str,
        entity_category: EntityCategory | None = None,
        repository_code: str | None = None,
        custom_key: str | None = None,
    ) -> None:
        """Add device sensor

        :param code: str: Sensor code
        :param name: str: Sensor name
        :param entity_category: EntityCategory | None: Entity category
        :param repository_code: str | None: Repository code
        :param custom_key: str | None: Custom key
        """

        if code in self.sensors:
            return

        self.sensors[code] = SeafileEntityDescription(
            description=SensorEntityDescription(
                key=code,
                name=name,
                icon="mdi:harddisk",
                native_unit_of_measurement=DATA_BYTES,
                state_class=SensorStateClass.TOTAL,
                entity_category=entity_category,
                entity_registry_enabled_default=True,
            ),
            device_info=self.device_info,
            custom_key=custom_key,
            repository_code=repository_code,
        )

        if self.new_sensor_callback:
            async_dispatcher_send(self.hass, SIGNAL_NEW_SENSOR, self.sensors[code])


@dataclass
class SeafileEntityDescription:
    """Seafile entity description."""

    description: EntityDescription
    device_info: DeviceInfo
    custom_key: str | None = None
    repository_code: str | None = None


@callback
def async_get_updater(hass: HomeAssistant, identifier: str) -> SeafileUpdater:
    """Return SeafileUpdater for username or entry id.

    :param hass: HomeAssistant
    :param identifier: str
    :return SeafileUpdater
    """

    if (
        DOMAIN not in hass.data
        or identifier not in hass.data[DOMAIN]
        or UPDATER not in hass.data[DOMAIN][identifier]
    ):
        raise ValueError(f"Integration with identifier: {identifier} not found.")

    return hass.data[DOMAIN][identifier][UPDATER]
