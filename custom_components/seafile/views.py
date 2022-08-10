""""Seafile view."""

from __future__ import annotations

import logging
import mimetypes
from hashlib import md5
from http import HTTPStatus
from typing import Any

from aiohttp import web
from aiohttp.hdrs import CACHE_CONTROL, ETAG
from aiohttp.typedefs import LooseHeaders
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, THUMBNAIL_SIZE
from .exceptions import SeafileError
from .helper import decode_path, encode_path, is_valid_uuid
from .updater import SeafileUpdater, async_get_updater

_LOGGER = logging.getLogger(__name__)


@callback
def async_generate_thumbnail_url(
    host: str,
    entry_id: str,
    repo_id: str,
    file_path: str,
    size: int = THUMBNAIL_SIZE,
) -> str:
    """Generate URL for event thumbnail.

    :param host: str: Current host
    :param entry_id: str: Entry id
    :param repo_id: str: Repository id
    :param file_path: str: File path
    :param size: str: Size
    :return str
    """

    return ThumbnailProxyView.mask.format(
        host=host.strip("/"),
        entry_id=entry_id,
        repo_id=repo_id,
        size=size,
        file_path=encode_path(file_path),
    )


class ThumbnailProxyView(HomeAssistantView):
    """View to proxy event thumbnails from Seafile."""

    requires_auth: bool = False

    mask: str = "{host}/api/seafile/thumbnail/{entry_id}/{repo_id}/{size}/{file_path}"
    url: str = "/api/seafile/thumbnail/{entry_id}/{repo_id}/{size}/{file_path:.*}"
    name: str = "api:seafile:thumbnail"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize a thumbnail proxy view."""

        self.hass = hass
        self.data = hass.data[DOMAIN]

    # pylint: disable=too-many-arguments
    async def get(
        self,
        request: web.Request,
        entry_id: str,
        repo_id: str,
        size: int,
        file_path: str,
    ) -> web.Response:
        """Get thumbnail

        :param request: web.Request: Request
        :param entry_id: str: Entry id
        :param repo_id: str: Repository id
        :param size: int: Thumbnail size
        :param file_path: str: File path
        :return web.Response
        """

        try:
            updater: SeafileUpdater = async_get_updater(self.hass, entry_id)
        except ValueError:
            return _404(f"Unable to find entry with id: {entry_id}")

        if not is_valid_uuid(repo_id):
            return _404(f"Unable to find library with id: {repo_id}")

        try:
            thumbnail: bytes = await updater.client.thumbnail(
                repo_id, decode_path(file_path), size
            )
        except SeafileError:
            return _404("Thumbnail not found")

        mime, _ = mimetypes.guess_type(file_path)

        headers: LooseHeaders = {
            CACHE_CONTROL: "public, max-age=31622400",
            ETAG: md5(thumbnail).hexdigest(),
        }

        return web.Response(body=thumbnail, content_type=mime, headers=headers)


@callback
def _404(message: Any) -> web.Response:
    return web.Response(body=message, status=HTTPStatus.NOT_FOUND)
