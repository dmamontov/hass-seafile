""""Seafile view."""

# pylint: disable=import-outside-toplevel

from __future__ import annotations

import io
import logging
import mimetypes
import shlex
import subprocess
from hashlib import md5
from http import HTTPStatus
from typing import Any

from aiohttp import web
from aiohttp.hdrs import CACHE_CONTROL, ETAG
from homeassistant.components.ffmpeg import FFmpegManager, get_ffmpeg_manager
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.media_player.const import MEDIA_CLASS_VIDEO
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, MIMETYPE_HEIC, MIMETYPE_JPEG, THUMBNAIL_SIZE
from .exceptions import SeafileError
from .helper import decode_path, encode_path, get_short_mime, is_valid_uuid
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

    # pylint: disable=too-many-arguments,too-many-locals
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

        size = int(size)  # sourcery skip

        try:
            updater: SeafileUpdater = async_get_updater(self.hass, entry_id)
        except ValueError:
            return _404(f"Unable to find entry with id: {entry_id}")

        if not is_valid_uuid(repo_id):
            return _404(f"Unable to find library with id: {repo_id}")

        mime, _ = mimetypes.guess_type(file_path)
        short_mime = get_short_mime(mime)

        thumbnail: bytes = b""

        try:
            if mime == MIMETYPE_HEIC:
                file: bytes = await updater.client.file(  # type: ignore
                    repo_id, decode_path(file_path), True
                )

                mime = MIMETYPE_JPEG
                thumbnail = await _convert_heic(file, size)
            elif short_mime == MEDIA_CLASS_VIDEO:  # pragma: no cover
                url: str = await updater.client.file(  # type: ignore
                    repo_id, decode_path(file_path)
                )

                mime = MIMETYPE_JPEG
                thumbnail = await _convert_video(self.hass, url.strip('"'), size)
            else:
                thumbnail = await updater.client.thumbnail(
                    repo_id, decode_path(file_path), size
                )
        except (SeafileError, ValueError, ModuleNotFoundError):
            return _404("Thumbnail not found")

        return web.Response(
            body=thumbnail,
            content_type=mime,
            headers={
                CACHE_CONTROL: "public, max-age=31622400",
                ETAG: md5(thumbnail).hexdigest(),
            },
        )


@callback
def _404(message: Any) -> web.Response:
    """404

    :param message: Any
    :return web.Response
    """

    return web.Response(body=message, status=HTTPStatus.NOT_FOUND)


async def _convert_heic(data: bytes, size: int | None = None) -> bytes:
    """Convert heic

    :param data: bytes
    :param size: int | None
    :return bytes
    """

    import PIL.Image
    import pyheif

    heif_file: pyheif.HeifFile = pyheif.read(data)

    image: PIL.Image = PIL.Image.frombytes(
        mode=heif_file.mode, size=heif_file.size, data=heif_file.data
    )

    if size and size > 0:
        image.thumbnail((size, size))

    buffer = io.BytesIO()

    image.save(buffer, format="jpeg")

    return buffer.getvalue()


async def _convert_video(
    hass: HomeAssistant, url: str, size: int
) -> bytes:  # pragma: no cover
    """Convert video

    :param hass: HomeAssistant
    :param url: str
    :param size: int
    :return bytes
    """

    manager: FFmpegManager = get_ffmpeg_manager(hass)

    def _convert(command: str) -> bytes:
        """Run convert

        :param command: str
        :return bytes
        """

        return subprocess.run(
            shlex.split(command), check=False, shell=False, stdout=subprocess.PIPE
        ).stdout

    return await hass.async_add_executor_job(
        _convert,
        str(
            f"{manager.binary} -loglevel quiet -i "
            f"{url} -frames:v 1 "
            f"-vf scale=-2:{size} -q:v 3 -f image2 -"
        ),
    )
