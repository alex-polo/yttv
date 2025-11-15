import enum
from typing import NamedTuple


class ContentMediaType(enum.Enum):
    """Type Content."""

    VIDEO = "video"
    PLAYLIST = "playlist"


class VideoFormatYouTube(NamedTuple):
    """Video format returned by YouTube."""

    format_note: str
    height: int
    ext: str
    vcodec: str
    dynamic_range: str
    resolution: str
    format: str

    def __eq__(self, value: object) -> bool:  # noqa: D105
        if not isinstance(value, VideoFormatYouTube):
            raise NotImplementedError

        return self.format_note == value.format_note

    def __hash__(self) -> int:  # noqa: D105
        return hash((self.format_note,))


class YouTubeContent(NamedTuple):
    """Content returned by YouTube via URL.."""

    media_type: ContentMediaType
    playlist_count: int | None
    title_video: str | None
    channel: str | None
    video_format_list: list[VideoFormatYouTube]
