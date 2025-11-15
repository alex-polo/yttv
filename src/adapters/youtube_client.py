import logging
import operator
from abc import abstractmethod
from collections.abc import Callable
from functools import reduce
from typing import Any, Protocol, runtime_checkable

import yt_dlp

from src.adapters.exceptions import (
    DownloadVideoByUrlError,
    FormatNoteNotSetError,
    RequestVideoDataByUrlError,
    VideoFormatsNotFoundError,
)
from src.schemas import (
    ContentMediaType,
    VideoFormatYouTube,
    YouTubeContent,
)

logger: logging.Logger = logging.getLogger(__name__)


@runtime_checkable
class YouTubeClientProtocol(Protocol):
    """Basic adapter protocol for interacting with YouTube."""

    @abstractmethod
    def request_video_data_by_url(  # noqa D102
        self,
        url: str,
        callback: Callable | None = None,
        **options: object,
    ) -> YouTubeContent: ...

    @abstractmethod
    def download(  # noqa D102
        self,
        url: str,
        callback: Callable | None = None,
        **options: object,
    ) -> None: ...


class YtDLPClientAdapter(YouTubeClientProtocol):
    """Downloader based on the yt_dlp library."""

    def __init__(
        self,
        ffmpeg_path: str,
        output_directory: str,
        retries: int,
        socket_timeout: int,
        http_headers: dict[str, str],
    ) -> None:
        """Initialize the yt-dlp-based YouTube client adapter."""
        self._ffmpeg_path: str = ffmpeg_path
        self._output_directory: str = output_directory
        self._retries = retries
        self._socket_timeout = socket_timeout
        self._http_headers = http_headers

    @classmethod
    def _parse_video_format_from_response(
        cls,
        ftm_data: dict,
    ) -> set[VideoFormatYouTube]:
        formats: list | None = ftm_data.get("formats")
        if not formats:
            raise VideoFormatsNotFoundError()

        received_formats: set[VideoFormatYouTube] = set()

        for fmt in formats:
            vcodec: str | None = fmt.get("vcodec", None)
            format_note: str | None = fmt.get("format_note")
            video_height: int | None = fmt.get("height")

            if vcodec and vcodec != "none" and format_note:
                if not video_height:
                    video_height = int(
                        "".join(
                            filter(str.isdigit, format_note.split("p")[0]),
                        ),
                    )
                video_format = VideoFormatYouTube(
                    format_note=format_note,
                    height=video_height,
                    ext=fmt.get("ext", "not specified"),
                    vcodec=vcodec,
                    dynamic_range=fmt.get("dynamic_range", "no"),
                    resolution=fmt.get("resolution", "no"),
                    format=fmt.get("format", "no"),
                )

                received_formats.add(video_format)

        return received_formats

    @classmethod
    def _parse_yt_dlp_reponse(cls, ydl_data: dict) -> YouTubeContent:
        playlist_count: int | None = ydl_data.get("playlist_count")
        title_video: str | None = ydl_data.get("title")
        channel: str | None = ydl_data.get("channel")

        common_formats: set[VideoFormatYouTube]
        media_type: ContentMediaType

        if "entries" in ydl_data:
            entries: dict = ydl_data["entries"]
            media_type = ContentMediaType.PLAYLIST
            format_list_of_sets: list[set[VideoFormatYouTube]] = [
                cls._parse_video_format_from_response(ftm_data=video_entry)
                for video_entry in entries
            ]

            common_formats = reduce(
                operator.and_,
                format_list_of_sets,
            )
        else:
            media_type = ContentMediaType.VIDEO

            common_formats = cls._parse_video_format_from_response(
                ftm_data=ydl_data,
            )

        return YouTubeContent(
            media_type=media_type,
            channel=channel,
            playlist_count=playlist_count,
            title_video=title_video,
            video_format_list=sorted(
                common_formats,
                key=lambda fmt: fmt.height,
            ),
        )

    def request_video_data_by_url(
        self,
        url: str,
        callback: Callable | None = None,
        **options: object,  # noqa: ARG002
    ) -> YouTubeContent:
        """Fetches video metadata from YouTube without downloading the content.

        Uses yt-dlp to extract full video information (formats, title)

        Args:
        url (str): Valid YouTube video or playlist URL.
        callback (Callable | None): Optional progress/status callback function.
        **options: Additional keyword arguments (currently unused but reserved
            for future extensibility).

        Returns:
        YouTubeContent: Parsed video or playlist metadata including available
            formats, title, media type, and other relevant information.

        Raises:
        RequestVideoDataByUrlError: If extraction fails.
        """
        ydl_opts: dict[
            str,
            str | list[Callable | None] | dict | int | logging.Logger,
        ] = {
            "extractor-args": {
                "youtube": {
                    "player_client": [
                        "web",
                        "web_embedded",
                        # "web",
                        # "tv",
                        # "ios",
                    ],
                },
            },
            "ffmpeg_location": self._ffmpeg_path,
            "skip_download": True,
            "quiet": True,
            "extract_flat": False,
            "logger": logger,
            "retries": self._retries,
            "socket_timeout": self._socket_timeout,
            "http_headers": self._http_headers,
            "progress_hooks": [callback],
        }
        try:
            # Pylance cannot resolve yt-dlp types;
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[reportArgumentType]
                ydl_data: Any | None = ydl.extract_info(
                    url=url,
                    download=False,
                )
        except Exception as exc:
            unexpected_error_msg = "An unexpected error occurred"
            raise RequestVideoDataByUrlError(
                unexpected_error_msg,
            ) from exc

        if not isinstance(ydl_data, dict):
            type_error_msg: str = (
                f"API YouTube gave incorrect data, a dictionary was "
                f"expected, but receivedtype: {type(ydl_data)}"
            )
            raise RequestVideoDataByUrlError(type_error_msg)

        youtube_content: YouTubeContent = self._parse_yt_dlp_reponse(
            ydl_data=ydl_data,
        )

        return youtube_content

    def download(
        self,
        url: str,
        callback: Callable | None = None,
        **options: object,
    ) -> None:
        """Downloads a YouTube video using yt-dlp with the specified format.

        Args:
            url (str): YouTube video URL to download.
            callback (Callable | None): Optional progress callback function.
            Receives status updates from yt-dlp.
            **options: Additional options. Must include 'format_note' (str).

        Raises:
            FormatNoteNotSetError: If 'format_note' is missing or not a string.
            DownloadVideoByUrlError: If the download fails for any reason.
        """
        outtmpl: str = f"{self._output_directory}/%(title)s.%(ext)s"

        height_option: object | None = options.get("format_height")
        if not isinstance(height_option, int):
            raise FormatNoteNotSetError()

        format_str: str = f"bestvideo[height={height_option}]+bestaudio"

        ydl_opts: dict[
            str,
            str | list[Callable | None] | dict | int | logging.Logger,
        ] = {
            "extractor-args": {
                "youtube": {
                    "player_client": [
                        "web",
                        "web_embedded",
                        # "tv",
                        # "ios",
                    ],
                },
            },
            "format": format_str,
            "outtmpl": outtmpl,
            "ffmpeg_location": self._ffmpeg_path,
            "progress_hooks": [callback],
            "retries": self._retries,
            "socket_timeout": self._socket_timeout,
            "http_headers": self._http_headers,
            "logger": logger,
        }

        try:
            # Pylance cannot resolve yt-dlp types;
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[import-untyped]
                ydl.download([url])
        except Exception as e:
            raise DownloadVideoByUrlError() from e
