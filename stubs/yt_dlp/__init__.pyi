# stubs/yt_dlp/__init__.pyi
"""Stub file for yt-dlp library."""

from typing import Any

class YoutubeDL:
    def __init__(
        self,
        params: dict[str, Any] | None = None,
    ) -> None: ...
    def __enter__(self) -> YoutubeDL: ...
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...  # noqa: ANN401
    def download(self, url_list: list[str]) -> None: ...
    def extract_info(
        self,
        url: str,
        download: bool = False,
    ) -> dict[str, Any]: ...
