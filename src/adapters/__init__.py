from collections.abc import Callable

from src.config.factory import ConfigFactory

from .youtube_client import YouTubeClientProtocol, YtDLPClientAdapter
from .youtube_factories import create_ytdlp_adapter_factory

YtDLPClientFactory: Callable[[ConfigFactory], YtDLPClientAdapter] = (
    create_ytdlp_adapter_factory
)

__all__: list[str] = [
    "YouTubeClientProtocol",
    "YtDLPClientAdapter",
    "YtDLPClientFactory",
]
