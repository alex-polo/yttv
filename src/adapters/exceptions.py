class YouTubeClientBaseError(Exception):
    """Base exception for YouTube client errors."""


class VideoFormatsNotFoundError(YouTubeClientBaseError):
    """Raised when no video formats are found for a given URL."""


class RequestVideoDataByUrlError(YouTubeClientBaseError):
    """Raised when failed to fetch video metadata from a URL."""


class DownloadVideoByUrlError(YouTubeClientBaseError):
    """Raised when video download fails."""


class FormatNoteNotSetError(YouTubeClientBaseError):
    """Raised when the required 'format_note' parameter is missing or empty."""
