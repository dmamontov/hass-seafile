"""Tests for the seafile component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,line-too-long

from __future__ import annotations

import json
import logging

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from httpx import HTTPError, Request
from pytest_homeassistant_custom_component.common import load_fixture
from pytest_httpx import HTTPXMock

from custom_components.seafile.client import SeafileClient
from custom_components.seafile.const import THUMBNAIL_SIZE
from custom_components.seafile.exceptions import (
    SeafileConnectionError,
    SeafileRequestError,
)
from tests.setup import (
    MOCK_PASSWORD,
    MOCK_URL,
    MOCK_USERNAME,
    get_url,
    load_image_fixture,
)

_LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_login(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Login test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    assert client._token == "911faaad4a082c4406a30a240ebd68a445f28c12"

    request: Request | None = httpx_mock.get_request(method="POST")
    assert request is not None
    assert request.url == get_url("auth-token")
    assert request.method == "POST"


@pytest.mark.asyncio
async def test_login_request_error(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Login request error"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    with pytest.raises(SeafileConnectionError):
        await client.login()


@pytest.mark.asyncio
async def test_login_no_field_error(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Login no field error"""

    httpx_mock.add_response(
        text=load_fixture("login_error_one_data.json"), method="POST", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    with pytest.raises(SeafileRequestError) as error:
        await client.login()

    assert (
        str(error.value)
        == "non_field_errors: Unable to login with provided credentials."
    )


@pytest.mark.asyncio
async def test_login_with_field_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Login with field error"""

    httpx_mock.add_response(
        text=load_fixture("login_error_two_data.json"), method="POST", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    with pytest.raises(SeafileRequestError) as error:
        await client.login()

    assert str(error.value) == "password: This field is required."


@pytest.mark.asyncio
async def test_login_incorrect_method_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Login incorrect method error"""

    httpx_mock.add_response(
        text=load_fixture("incorrect_method_data.json"), method="POST", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    with pytest.raises(SeafileRequestError) as error:
        await client.login()

    assert str(error.value) == 'Method "GET" not allowed.'


@pytest.mark.asyncio
async def test_login_empty_response_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Login empty response error"""

    httpx_mock.add_response(
        text=load_fixture("empty_response.json"), method="POST", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    with pytest.raises(SeafileRequestError) as error:
        await client.login()

    assert str(error.value) == "Request error."


@pytest.mark.asyncio
async def test_login_empty_field_error_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Login empty field error error"""

    httpx_mock.add_response(
        text=load_fixture("login_error_three_data.json"), method="POST", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    with pytest.raises(SeafileRequestError) as error:
        await client.login()

    assert str(error.value) == "Request error."


@pytest.mark.asyncio
async def test_account(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Account test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("account_data.json"), method="GET")

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    assert await client.account() == json.loads(load_fixture("account_data.json"))

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("account/info")
    assert request.method == "GET"


@pytest.mark.asyncio
async def test_error_account(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Account error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_exception(exception=HTTPError, method="GET")  # type: ignore

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileConnectionError):
        await client.account()


@pytest.mark.asyncio
async def test_request_error_account(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Account request error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("incorrect_method_data.json"), method="GET", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileRequestError):
        await client.account()


@pytest.mark.asyncio
async def test_libraries(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Libraries test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("libraries_data.json"), method="GET")

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    assert await client.libraries() == json.loads(load_fixture("libraries_data.json"))

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("repos", {"type": "mine"})
    assert request.method == "GET"


@pytest.mark.asyncio
async def test_error_libraries(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Libraries error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_exception(exception=HTTPError, method="GET")  # type: ignore

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileConnectionError):
        await client.libraries()


@pytest.mark.asyncio
async def test_request_error_libraries(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Libraries request error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("incorrect_method_data.json"), method="GET", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileRequestError):
        await client.libraries()


@pytest.mark.asyncio
async def test_server(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Server test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("server_data.json"), method="GET")

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    assert await client.server() == json.loads(load_fixture("server_data.json"))

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("server-info")
    assert request.method == "GET"


@pytest.mark.asyncio
async def test_error_server(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Server error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_exception(exception=HTTPError, method="GET")  # type: ignore

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileConnectionError):
        await client.server()


@pytest.mark.asyncio
async def test_request_error_server(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Server request error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("incorrect_method_data.json"), method="GET", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileRequestError):
        await client.server()


@pytest.mark.asyncio
async def test_directories(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Directories test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("dir_root_data.json"), method="GET")

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    assert await client.directories("test") == json.loads(
        load_fixture("dir_root_data.json")
    )

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("repos/test/dir")
    assert request.method == "GET"


@pytest.mark.asyncio
async def test_error_directories(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Directories error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_exception(exception=HTTPError, method="GET")  # type: ignore

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileConnectionError):
        await client.directories("test")


@pytest.mark.asyncio
async def test_request_error_directories(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Directories request error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("incorrect_method_data.json"), method="GET", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileRequestError):
        await client.directories("test")


@pytest.mark.asyncio
async def test_file(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """File test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(text=load_fixture("file_data.txt"), method="GET")

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    assert await client.file("test", "/") == load_fixture("file_data.txt")

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url("repos/test/file", {"p": "/", "reuse": 1})
    assert request.method == "GET"


@pytest.mark.asyncio
async def test_error_file(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """File error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_exception(exception=HTTPError, method="GET")  # type: ignore

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileConnectionError):
        await client.file("test", "/")


@pytest.mark.asyncio
async def test_request_error_file(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """File request error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("incorrect_method_data.json"), method="GET", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileRequestError):
        await client.file("test", "/")


@pytest.mark.asyncio
async def test_thumbnail(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Thumbnail test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        content=load_image_fixture("thumbnail_data.jpg"), method="GET"
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    assert await client.thumbnail("test", "/") == load_image_fixture(
        "thumbnail_data.jpg"
    )

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url(
        "repos/test/thumbnail", {"p": "/", "size": THUMBNAIL_SIZE}
    )
    assert request.method == "GET"


@pytest.mark.asyncio
async def test_thumbnail_with_encode(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Thumbnail test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        content=load_image_fixture("thumbnail_data.jpg"), method="GET"
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    assert await client.thumbnail("test", "/1+(1+из+624).jpg") == load_image_fixture(
        "thumbnail_data.jpg"
    )

    request: Request | None = httpx_mock.get_request(method="GET")
    assert request is not None
    assert request.url == get_url(
        "repos/test/thumbnail", {"p": "/1+(1+из+624).jpg", "size": THUMBNAIL_SIZE}
    )
    assert request.method == "GET"


@pytest.mark.asyncio
async def test_error_thumbnail(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Thumbnail error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_exception(exception=HTTPError, method="GET")  # type: ignore

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileConnectionError):
        await client.thumbnail("test", "/")


@pytest.mark.asyncio
async def test_request_error_thumbnail(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Thumbnail request error test"""

    httpx_mock.add_response(text=load_fixture("login_data.json"), method="POST")
    httpx_mock.add_response(
        text=load_fixture("incorrect_method_data.json"), method="GET", status_code=400
    )

    client: SeafileClient = SeafileClient(
        get_async_client(hass, False), MOCK_URL, MOCK_USERNAME, MOCK_PASSWORD
    )

    await client.login()

    with pytest.raises(SeafileRequestError):
        await client.thumbnail("test", "/")
