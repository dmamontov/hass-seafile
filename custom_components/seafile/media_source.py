"""Media source component."""


from __future__ import annotations

import contextlib
import logging
import mimetypes
from operator import itemgetter

from homeassistant.components.media_player.const import (
    MEDIA_CLASS_APP,
    MEDIA_CLASS_DIRECTORY,
    MEDIA_CLASS_IMAGE,
)
from homeassistant.components.media_source.const import (
    MEDIA_CLASS_MAP,
    MEDIA_MIME_TYPES,
)
from homeassistant.components.media_source.error import MediaSourceError, Unresolvable
from homeassistant.components.media_source.models import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import (
    ATTR_AVATAR_URL,
    ATTR_REPOSITORIES,
    ATTR_REPOSITORY_NAME,
    ATTR_STATE,
    DOMAIN,
    MIMETYPE_HEIC,
    MIMETYPE_JPEG,
    THUMBNAIL_SIZE,
)
from .exceptions import SeafileError
from .helper import get_short_mime, is_valid_uuid
from .updater import SeafileUpdater, async_get_updater
from .views import async_generate_thumbnail_url

_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> SeafileMediaSource:
    """Set up seafile media source

    :param hass: HomeAssistant: HomeAssistant object
    :return SeafileMediaSource
    """

    return SeafileMediaSource(hass)


class SeafileMediaSource(MediaSource):
    """Provide seafile media sources."""

    name: str = "Seafile"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize MotionEyeMediaSource.

        :param hass: HomeAssistant: HomeAssistant object
        """

        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a media item to a playable item.

        :param item: MediaSourceItem: MediaSourceItem object
        :return PlayMedia
        """

        path: list = item.identifier.split("/")

        if not is_valid_uuid(path[1]):
            raise Unresolvable(f"Unable to find library with id: {path[1]}")

        try:
            updater: SeafileUpdater = async_get_updater(self.hass, path[0])
        except ValueError as _e:
            raise Unresolvable(f"Unable to find entry with id: {path[0]}") from _e

        mime, _ = mimetypes.guess_type(path[-1])

        url: str = ""

        if mime == MIMETYPE_HEIC:  # pragma: no cover
            url = async_generate_thumbnail_url(
                _get_host(self.hass), path[0], path[1], f"/{'/'.join(path[2:])}", 0
            )
            mime = MIMETYPE_JPEG
        else:
            try:
                url = await updater.client.file(path[1], f"/{'/'.join(path[2:])}")  # type: ignore
            except SeafileError as _e:
                raise Unresolvable(
                    f"Could not resolve media item: {item.identifier}"
                ) from _e

        return PlayMedia(url=url.strip('"'), mime_type=mime)

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse media.

        :param item: MediaSourceItem: MediaSourceItem object
        :return BrowseMediaSource
        """

        if not item.identifier:
            return self._build_root()

        path: list = item.identifier.split("/")

        if len(path) == 1:
            return self._build_entry(item.identifier)

        if not is_valid_uuid(path[1]):
            raise MediaSourceError(f"Unable to find library with id: {path[1]}")

        try:
            updater: SeafileUpdater = async_get_updater(self.hass, path[0])
        except ValueError as _e:
            raise MediaSourceError(f"Unable to find entry with id: {path[0]}") from _e

        if len(path) == 2:
            source: BrowseMediaSource = self._build_library(  # type: ignore
                path[0],
                path[1],
                updater.data.get(ATTR_REPOSITORIES, {})
                .get(path[1], {})
                .get(ATTR_REPOSITORY_NAME, "Library"),
            )
        else:
            source: BrowseMediaSource = self._build_dir(item.identifier, path[-1])  # type: ignore

        source.children = await self._build_path(
            updater, item.identifier, path[1], f"/{'/'.join(path[2:])}"
        )

        return source

    def _build_root(self) -> BrowseMediaSource:
        """Build the media sources for config entries.

        :return BrowseMediaSource
        """

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier="",
            media_class=MEDIA_CLASS_APP,
            media_content_type="",
            title=self.name,
            can_play=False,
            can_expand=True,
            children=[
                self._build_entry(entry.entry_id)
                for entry in self.hass.config_entries.async_entries(DOMAIN)
            ],
            children_media_class=MEDIA_CLASS_APP,
        )

    def _build_entry(self, entry_id: str) -> BrowseMediaSource:
        """Build the media sources for config entry.

        :param entry_id: str
        :return BrowseMediaSource
        """

        try:
            updater: SeafileUpdater = async_get_updater(self.hass, entry_id)
        except ValueError as _e:
            raise MediaSourceError(f"Unable to find entry with id: {entry_id}") from _e

        state: bool = updater.data.get(ATTR_STATE, False)

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=entry_id,
            media_class=MEDIA_CLASS_APP,
            media_content_type="",
            title=updater.username,
            thumbnail=updater.data.get(ATTR_AVATAR_URL, None),
            can_play=False,
            can_expand=state,
            children=[
                self._build_library(
                    entry_id, _id, data.get(ATTR_REPOSITORY_NAME, "Library"), state
                )
                for _id, data in updater.data.get(ATTR_REPOSITORIES, {}).items()
            ],
            children_media_class=MEDIA_CLASS_DIRECTORY,
        )

    def _build_library(
        self, entry_id: str, repo_id: str, name: str, state: bool = True
    ) -> BrowseMediaSource:
        """Build the media sources for libraries.

        :param entry_id: str
        :param repo_id: str
        :param name: str
        :param state: bool
        :return BrowseMediaSource
        """

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{entry_id}/{repo_id}",
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_type="",
            title=name,
            can_play=False,
            can_expand=state,
            children_media_class=MEDIA_CLASS_DIRECTORY,
        )

    def _build_dir(self, identifier: str, name: str) -> BrowseMediaSource:
        """Build the media sources for dir.

        :param identifier: str
        :param name: str
        :return BrowseMediaSource
        """

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{identifier}/{name}",
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_type="",
            title=name,
            can_play=False,
            can_expand=True,
            children_media_class=MEDIA_CLASS_DIRECTORY,
        )

    def _build_file(self, identifier: str, name: str, mime: str) -> BrowseMediaSource:
        """Build the media sources for file.

        :param identifier: str
        :param name: str
        :param mime: str
        :return BrowseMediaSource
        """

        thumbnail: str | None = None
        if mime == MEDIA_CLASS_IMAGE:
            path: list = identifier.split("/")

            thumbnail = async_generate_thumbnail_url(
                _get_host(self.hass),
                path[0],
                path[1],
                f"{'/'.join(path[2:])}/{name}",
                THUMBNAIL_SIZE,
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{identifier}/{name}",
            media_class=MEDIA_CLASS_MAP[mime],
            media_content_type=MEDIA_CLASS_MAP[mime],
            thumbnail=thumbnail,
            title=name,
            can_play=True,
            can_expand=False,
        )

    async def _build_path(
        self, updater: SeafileUpdater, identifier: str, repo_id: str, path: str
    ) -> list[BrowseMediaSource]:
        # sourcery skip: avoid-builtin-shadow
        """Build the media sources from path.

        :param updater: SeafileUpdater
        :param identifier: str
        :param repo_id: str
        :param path: str
        :return list[BrowseMediaSource]
        """

        try:
            response = await updater.client.directories(repo_id, path)
        except SeafileError as _e:
            raise MediaSourceError(f"Unable to find path: {path}") from _e

        directories: list = sorted(
            [element for element in response if element.get("type", None) == "dir"],
            key=itemgetter("name", "mtime"),
        )

        sources = [
            self._build_dir(identifier, directory.get("name").replace("&nbsp", ""))
            for directory in directories
        ]

        files: list = sorted(
            [element for element in response if element.get("type", None) == "file"],
            key=itemgetter("mtime", "name"),
            reverse=True,
        )

        for file in files:
            mime, _ = mimetypes.guess_type(file.get("name"))
            mime = get_short_mime(mime)

            if mime not in MEDIA_MIME_TYPES:
                continue

            sources.append(
                self._build_file(
                    identifier,
                    file.get("name").replace("&nbsp", ""),
                    mime,  # type: ignore
                )
            )

        return sources


def _get_host(hass: HomeAssistant) -> str:
    """Get host from HomeAssistant

    :param hass: HomeAssistant
    :return str
    """
    host: str = get_url(hass)
    with contextlib.suppress(NoURLAvailableError):
        host = get_url(hass, require_current_request=True)

    return host
