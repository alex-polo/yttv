import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from src.adapters.exceptions import (
    DownloadVideoByUrlError,
    FormatNoteNotSetError,
    YouTubeClientBaseError,
)
from src.adapters.youtube_client import YouTubeClientProtocol
from src.config.classes import BaseConfiguration, ProjectInfo, ProjectSettings
from src.ui import RichUI

if TYPE_CHECKING:
    from src.schemas import YouTubeContent

logger: logging.Logger = logging.getLogger(__name__)


ConfigType = TypeVar("ConfigType", bound=BaseConfiguration)


class BaseStep(ABC):
    """Base abstract class for a processing pipeline step."""

    def __init__(self, **kwargs: object) -> None:
        """Initialize the step with provided dependencies.

        Args:
            **kwargs: Keyword arguments containing step dependencies such as
                      UI interface, YouTube adapter, configuration objects.
        """
        self.options: dict[str, Any] = kwargs

    @staticmethod
    def _validate_url(url: str | None) -> str:
        """Validate that the provided URL is a non-empty string.

        Args:
            url: The URL string to validate.

        Returns:
            A stripped, non-empty URL string.

        Raises:
            TypeError: If the URL is not a string or is empty/whitespace-only.
        """
        if not isinstance(url, str) or not url.strip():
            type_error_url_msg = "URL must be a non-empty string"
            raise TypeError(type_error_url_msg)

        return url

    def _get_ui_interface(self) -> RichUI:
        """Retrieve the user interface (UI) dependency.

        The UI instance must be passed in `options` during step initialization.

        Returns:
            An instance of RichUI for displaying messages, progress bars, etc.

        Raises:
            TypeError: If the UI is missing or is not an instance of RichUI.
        """
        ui: RichUI | None = self.options.get("ui")
        if not isinstance(ui, RichUI):
            ui_type_error_msg: str = "Type of UI interface is None."
            raise TypeError(ui_type_error_msg)

        return ui

    def _get_config_by_name(
        self,
        config_name: str,
        config_type: type[ConfigType],
    ) -> ConfigType:
        """Retrieve a configuration object by name and validate its type.

        Args:
            config_name: The key under which the config.
            config_type: The expected type of the configuration object.

        Returns:
            A configuration instance of the specified type.

        Raises:
            TypeError: If the config is missing or does
                       not match the expected type.
        """
        config: ConfigType | None = self.options.get(
            config_name,
        )

        if not isinstance(config, config_type):
            config_type_error_msg: str = (
                f"Configuration '{config_name}' "
                f"is not an instance of {config_type.__name__}. "
                f"Got {type(config).__name__} instead."
            )
            raise TypeError(config_type_error_msg)

        return config

    def _get_youtube_adapter(self) -> YouTubeClientProtocol:
        """Retrieve the YouTube client adapter dependency.

        The adapter must be passed in `options` during step initialization.

        Returns:
            An object implementing the YouTubeClientProtocol interface.

        Raises:
            TypeError: If the adapter is missing or
                       does not implement YouTubeClientProtocol.
        """
        youtube_adapter: YouTubeClientProtocol | None = self.options.get(
            "youtube_adapter",
        )

        if not isinstance(youtube_adapter, YouTubeClientProtocol):
            type_error_adapter_msg: str = (
                f"YouTube adapter is not valid. "
                f"Got {type(youtube_adapter).__name__} ({youtube_adapter!r}) "
                f"instead of YouTubeClientProtocol."
            )
            raise TypeError(type_error_adapter_msg)

        return youtube_adapter

    def execute(self, context: dict[str, Any]) -> bool:
        """Template method to execute the step.

        Delegates to the abstract `_run` method with the provided context.
        Can be extended in subclasses.

        Args:
            context: A dictionary containing data shared between pipeline steps
                (e.g., URL, selected format, file paths ...).

        Returns:
            True if the step succeeded, False otherwise.
        """
        return self._run(context)

    @abstractmethod
    def _run(self, context: dict[str, Any]) -> bool:
        """Execute the core logic of the step.

        Must be implemented by concrete subclasses.
        Uses dependencies from `self.options` and data from the context.

        Args:
            context: A dictionary containing input data required for execution.

        Returns:
            True on success, False on failure.
        """


class ShowGreetingStep(BaseStep):
    """Displays a greeting message with project information."""

    def _run(self, context: dict[str, Any]) -> bool:  # noqa: ARG002
        ui: RichUI = self._get_ui_interface()

        project_info: ProjectInfo = self._get_config_by_name(
            "project_info",
            ProjectInfo,
        )

        ui.show_greeting(
            name=project_info.name,
            version=project_info.version,
            description=project_info.description,
        )

        return True


class GetURLStep(BaseStep):
    """Prompts the user to input a YouTube video URL."""

    def _run(self, context: dict[str, Any]) -> bool:
        ui: RichUI = self._get_ui_interface()

        project_settings: ProjectSettings = self._get_config_by_name(
            "project_settings",
            ProjectSettings,
        )

        url: str = ui.request_url_from_user(
            domains_youtube=project_settings.domains_youtube,
        )
        context["url"] = url

        return True


class RequestFormatsByURLStep(BaseStep):
    """Fetches available video formats and metadata from a YouTube URL."""

    def _run(self, context: dict[str, Any]) -> bool:
        ui: RichUI = self._get_ui_interface()
        try:
            with ui.show_spinner(
                message="- Download data from the link",
            ):
                url: str = self._validate_url(url=context.get("url"))

                youtube_adapter: YouTubeClientProtocol = (
                    self._get_youtube_adapter()
                )
                youtube_content: YouTubeContent = (
                    youtube_adapter.request_video_data_by_url(
                        url=url,
                    )
                )
                context["youtube_content"] = youtube_content

        except (YouTubeClientBaseError, TypeError):
            request_failed_msg = "Failed to request data from the URL."
            logger.exception(msg=request_failed_msg)
            ui.show_error_msg(msg=request_failed_msg)
            return False
        else:
            return True


class RequiredFormatFromUserStep(BaseStep):
    """Prompts the user to select a video format for download."""

    def _run(self, context: dict[str, Any]) -> bool:
        ui: RichUI = self._get_ui_interface()
        youtube_content: YouTubeContent = context.get("youtube_content")  # type: ignore

        selected_video_id: int = ui.request_video_formats_from_user(
            content=youtube_content,
        )
        context["selected_format_height"] = youtube_content.video_format_list[
            selected_video_id - 1
        ].height

        return True


class RequiredDirectoryFromUserStep(BaseStep):
    """Prompts the user to specify a download output directory."""

    def _run(self, context: dict[str, Any]) -> bool:
        ui: RichUI = self._get_ui_interface()
        output_dir: Path = context.get("output_dir", Path.cwd())

        context["output_dir"] = ui.request_directory_from_user(
            default_output_dir=output_dir.as_posix(),
        )

        return True


class DownloadVideoStep(BaseStep):
    """Download video or playlist from a YouTube URL."""

    @staticmethod
    def _truncate_filename(
        path_to_file: str | None,
        max_filename_length: int = 80,
    ) -> str:
        if not path_to_file:
            filename = "N/A"
        else:
            file_path = Path(path_to_file)

            if len(file_path.name) > max_filename_length:
                adding_smb: str = "... "
                file_stem: str = file_path.stem
                suffix: str = file_path.suffix
                available_length: int = (
                    max_filename_length - len(adding_smb) - len(suffix)
                )
                filename = (
                    f"{file_stem[:available_length]}{adding_smb}{suffix}"
                )
            else:
                filename = file_path.name

        return filename

    def _run(self, context: dict[str, Any]) -> bool:
        ui: RichUI = self._get_ui_interface()
        url: str = self._validate_url(url=context.get("url"))
        selected_format_height = context["selected_format_height"]

        with ui.download_progress_bar(
            "Preparing ...",
            total=100,
        ) as (
            progress,
            task_id,
        ):
            current_file_path: str | None = None
            filename: str = "N/A"

            def callback(data: dict) -> None:
                nonlocal progress, task_id, current_file_path, filename

                data_file_path: str | None = data.get("filename")

                if current_file_path != data_file_path:
                    current_file_path = data_file_path
                    filename = self._truncate_filename(
                        path_to_file=data_file_path,
                    )

                if data["status"] == "error":
                    ui.show_error_msg("Failed to Download data from the URL.")
                    download_error_msg = f"Download error: {data.get('error')}"
                    logger.error(download_error_msg)

                elif data["status"] == "downloading":
                    progress.update(
                        task_id,
                        description=f"# Download\nFile: {filename}",
                    )
                    percent_str: str = (
                        data.get("_percent_str", "0%").replace("%", "").strip()
                    )
                    current_percent = float(percent_str)
                    progress.update(task_id, completed=current_percent)

                elif data["status"] == "finished":
                    ui.show_success_msg(f"{filename} - downloaded.")

            try:
                youtube_adapter: YouTubeClientProtocol = (
                    self._get_youtube_adapter()
                )
                youtube_adapter.download(
                    url=url,
                    callback=callback,
                    format_height=selected_format_height,
                )
            except DownloadVideoByUrlError:
                download_error_msg: str = (
                    "An error occurred while downloading the video."
                )
                ui.show_error_msg(download_error_msg)
                logger.exception(download_error_msg)
                return False

            except FormatNoteNotSetError:
                format_error_msg = "Format note not founded in context."
                ui.show_error_msg(format_error_msg)
                logger.exception(format_error_msg)
                return False

        return True


class FinishStep(BaseStep):
    """Final step of the execution pipeline."""

    def _run(self, context: dict[str, Any]) -> bool:  # noqa: ARG002
        ui: RichUI = self._get_ui_interface()
        ui.show_text("Complete!")
        return True
