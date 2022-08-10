"""Seafile API client."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from homeassistant.const import CONF_PASSWORD, CONF_TOKEN, CONF_TYPE, CONF_USERNAME
from httpx import AsyncClient, ConnectError, HTTPError, Response, TransportError

from .const import (
    CLIENT_URL,
    DEFAULT_TIMEOUT,
    DIAGNOSTIC_CONTENT,
    DIAGNOSTIC_DATE_TIME,
    DIAGNOSTIC_MESSAGE,
    THUMBNAIL_SIZE,
)
from .exceptions import SeafileConnectionError, SeafileRequestError

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods,too-many-arguments
class SeafileClient:
    """Seafile API Client."""

    _client: AsyncClient
    _timeout: int = DEFAULT_TIMEOUT

    _url: str

    _username: str
    _password: str
    _token: str | None = None

    def __init__(
        self,
        client: AsyncClient,
        url: str,
        username: str,
        password: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize API client.

        :param client: AsyncClient: AsyncClient object
        :param url: str: URL address
        :param username: str: Username
        :param password: str: Password
        :param timeout: int: Query execution timeout
        """

        url = url.removesuffix("/")
        self._client = client
        self._timeout = timeout

        self._url = CLIENT_URL.format(url=url)

        self._username = username
        self._password = password

        self.diagnostics: dict[str, Any] = {}

    async def request(
        self, path: str, body: dict | None = None, string_response: bool = False
    ) -> dict | list | str | bytes:
        """Request method.

        :param path: str: api path
        :param body: dict | None: api body
        :param string_response: bool: Is string response
        :return dict | list | str | bytes: dict or list or str or bytes with api data.
        """

        _url: str = f"{self._url}/{path}/"

        try:
            async with self._client as client:
                response: Response = await client.get(
                    _url,
                    params=body,
                    headers={"Authorization": f"Token {self._token}"},
                    timeout=self._timeout,
                )

            self._debug("Successful request", _url, response.content, path)

            if string_response and response.status_code < 400:

                try:
                    return response.content.decode("utf-8")
                except UnicodeDecodeError:
                    return response.content

            _data: dict | list = json.loads(response.content)
        except (
            HTTPError,
            ConnectError,
            TransportError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as _e:
            self._debug("Connection error", _url, _e, path)

            raise SeafileConnectionError("Connection error") from _e

        if response.status_code >= 400:
            self._raise(_data)

        return _data

    async def login(self) -> None:
        """login method."""

        _path: str = "auth-token"
        _url: str = f"{self._url}/{_path}/"

        try:
            async with self._client as client:
                response: Response = await client.post(
                    _url,
                    data={
                        CONF_USERNAME: self._username,
                        CONF_PASSWORD: self._password,
                    },
                    timeout=self._timeout,
                )

            self._debug("Successful request", _url, response.content, _path)

            _data: dict = json.loads(response.content)
        except (
            HTTPError,
            ConnectError,
            TransportError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as _e:
            self._debug("Connection error", _url, _e, _path)

            raise SeafileConnectionError("Connection error") from _e

        if response.status_code >= 400:
            self._raise(_data)

        if CONF_TOKEN in _data:
            self._token = _data.get(CONF_TOKEN)

    async def account(self) -> dict:
        """Get account info

        :return dict: Response data
        """

        return dict(await self.request("account/info"))  # type: ignore

    async def server(self) -> dict:
        """Get server info

        :return dict: Response data
        """

        return dict(await self.request("server-info"))  # type: ignore

    async def libraries(self) -> list:
        """Get libraries

        :return list: Response data
        """

        return list(await self.request("repos", {CONF_TYPE: "mine"}))

    async def directories(self, repo_id: str, path: str | None = None) -> list:
        """Get directories

        :param repo_id: str
        :param path: str | None
        :return list: Response data
        """

        return list(
            await self.request(f"repos/{repo_id}/dir", {"p": path} if path else None)
        )

    async def file(self, repo_id: str, path: str) -> str:
        """Get file

        :param repo_id: str
        :param path: str
        :return str: Response str
        """

        return str(
            await self.request(f"repos/{repo_id}/file", {"p": path, "reuse": 1}, True)
        )

    async def thumbnail(
        self, repo_id: str, path: str, size: int = THUMBNAIL_SIZE
    ) -> bytes:
        """Get file

        :param repo_id: str
        :param path: str
        :param size: int
        :return bytes: Response bytes
        """

        path = path.strip("/")

        return bytes(
            await self.request(  # type: ignore
                f"repos/{repo_id}/thumbnail", {"p": f"/{path}", "size": size}, True
            )
        )

    @staticmethod
    def _raise(response: dict | list) -> None:
        """Parse errors.

        :param response: dict | list: Response data
        """

        if not response or isinstance(response, list):
            raise SeafileRequestError("Request error.")

        _errors: list = []

        for field, errors in response.items():
            if not errors:
                continue

            if isinstance(errors, str):
                _errors.append(errors)

                continue

            if isinstance(errors, list):
                _errors.append(f"{field}: " + "; ".join(errors))

        raise SeafileRequestError(".\n".join(_errors) if _errors else "Request error.")

    def _debug(self, message: str, url: str, content: Any, path: str) -> None:
        """Debug log

        :param message: str: Message
        :param url: str: URL
        :param content: Any: Content
        :param path: str: Path
        """

        _LOGGER.debug("%s (%s): %s", message, url, str(content))

        _content: dict | str = {}

        try:
            _content = json.loads(content)
        except (ValueError, TypeError):  # pragma: no cover
            _content = str(content)

        self.diagnostics[path] = {
            DIAGNOSTIC_DATE_TIME: datetime.now().replace(microsecond=0).isoformat(),
            DIAGNOSTIC_MESSAGE: message,
            DIAGNOSTIC_CONTENT: _content,
        }
