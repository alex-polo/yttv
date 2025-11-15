from typing import TYPE_CHECKING

from src.config.factory import ConfigFactory

from .youtube_client import YtDLPClientAdapter

if TYPE_CHECKING:
    from src.config.classes import ProjectSettings


def create_ytdlp_adapter_factory(
    config_factory: ConfigFactory,
) -> YtDLPClientAdapter:
    """Create factory for YouTube adapter with settings from config.

    Args:
        config_factory: Factory for creating configuration objects.

    Returns:
        YtDLPClientAdapter: Configured YouTube adapter instance.
    """
    settings: ProjectSettings = config_factory.create_project_settings()
    ffmpeg_path = str(settings.ffmpeg_path)
    output_directory = str(settings.output_dir)
    return YtDLPClientAdapter(
        ffmpeg_path=ffmpeg_path,
        output_directory=output_directory,
        retries=settings.network_retries,
        socket_timeout=settings.network_socket_timeout,
        http_headers=settings.network_http_headers,
    )
