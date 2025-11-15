import pathlib
from collections.abc import Generator
from contextlib import contextmanager
from typing import Final
from urllib.parse import ParseResult, urlparse
from venv import logger

import pyfiglet
from rich.console import Console, JustifyMethod
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskID, TextColumn
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from src.schemas import ContentMediaType, YouTubeContent


class RichUI:
    """Rich UI interface."""

    __slots__ = (
        "_console",
        "_style_error_text",
        "_style_format_block",
        "_style_format_block_green_yellow",
        "_style_format_note",
        "_style_format_table",
        "_style_format_table_justify",
        "_style_format_table_title",
        "_style_greeting_border",
        "_style_greeting_logo_font",
        "_style_greeting_logo_text",
        "_style_greeting_panel_justify",
        "_style_greeting_text",
        "_style_success_text",
        "_style_text",
    )

    def __init__(self) -> None:
        """Initializes the UI interface with a Rich console."""
        # Greeting
        self._style_greeting_text: str = "bold bright_black"
        self._style_greeting_border = "steel_blue3"
        self._style_greeting_logo_font: str = "slant"
        self._style_greeting_logo_text = "bold steel_blue1"
        self._style_greeting_panel_justify: JustifyMethod = "center"

        # Formats
        self._style_format_table_justify = "left"
        self._style_format_table = "bold cyan"
        self._style_format_table_title = "green_yellow"
        self._style_format_note = "green"
        self._style_format_block = "bold green_yellow"
        self._style_format_block_green_yellow = "green_yellow"

        # Error
        self._style_error_text: str = "bold red3"

        # Success
        self._style_success_text = "bold green"

        # Other
        self._style_text: str = "white"

        self._console: Final[Console] = Console(style=self._style_text)

    def show_success_msg(self, msg: str) -> None:
        """Displays a success message.

        Args:
            msg (str): The success message to display.
        """
        text = Text(f"# SUCCESS | {msg}", style=self._style_success_text)
        self._console.print(text)

    def show_error_msg(self, msg: str) -> None:
        """Displays an error message in bold red text.

        Args:
            msg (str): The error message to display.
        """
        text = Text(
            f"# ERROR | {msg} See the log file for details.",
            style=self._style_error_text,
        )
        self._console.print(text)

    def show_text(self, msg: str) -> None:
        """Displays an message text.

        Args:
            msg (str): The error message to display.
        """
        self._console.print(
            Text(
                msg,
                style=self._style_text,
            ),
        )

    def show_split_line(self) -> None:
        """Displays an split line message in bold green text."""
        text = Text(
            "-" * 150,
            style=self._style_success_text,
        )
        self._console.print(text)

    def show_greeting(self, name: str, version: str, description: str) -> None:
        """Displays a stylized welcome banner at program startup.

        Args:
            name (str): Application name (used for ASCII art and title).
            version (str): Application version string.
            description (str): Brief description of the application.
        """
        panel_title = Text(name, style=self._style_greeting_text)
        panel_subtitle = Text(
            f"version: {version}",
            style=self._style_greeting_text,
        )

        panel_renderable: Text = Text()
        panel_renderable.append(
            pyfiglet.figlet_format(
                name,
                font=self._style_greeting_logo_font,
            ),
            style=self._style_greeting_logo_text,
        )
        panel_renderable.append(
            "─" * 50 + "\n",
            style=self._style_greeting_text,
        )
        panel_renderable.append(
            f"{description}",
            style=self._style_greeting_text,
        )

        panel = Panel(
            title=panel_title,
            subtitle=panel_subtitle,
            subtitle_align="right",
            renderable=panel_renderable,
            padding=(1, 0),
            width=100,
            border_style=self._style_greeting_border,
        )
        self._console.print(panel, justify=self._style_greeting_panel_justify)

    def request_url_from_user(self, domains_youtube: set[str]) -> str:
        """Prompts the user to enter a valid YouTube video URL.

        Accepts only HTTPS URLs with a domain from the allowed set.
        Keeps asking until a valid URL is provided.

        Args:
        domains_youtube (set[str]): Allowed YouTube domains for URL validation.

        Returns:
            str: A validated HTTPS URL with an allowed YouTube domain.
        """
        while True:
            url: str = Prompt.ask(
                "YouTube video URL",
            ).strip()

            parsed_url: ParseResult = urlparse(url)
            validate_result: bool = parsed_url.netloc in domains_youtube

            if not validate_result or parsed_url.scheme != "https":
                self._console.print(
                    Text("Incorrect video URL", style=self._style_error_text),
                )
                continue

            break

        return url

    def request_video_formats_from_user(self, content: YouTubeContent) -> int:
        """Prompt the user to select a video format from the available list.

        Displays a formatted table of available video formats with their IDs,
        format notes, and resolutions. Additionally shows contextual
        information about the media (video title for single videos or playlist
        size for playlists).
        The user is asked to enter a valid format ID, with the highest-quality
        format (last in the list) selected by default.

        Args:
            content (YouTubeContent): An object containing video format
            metadata and media type information (either VIDEO or PLAYLIST).

        Returns:
            int: The 1-based ID of the selected video format corresponding to
            its position in `content.video_format_list`.
        """
        unavailable_status = "Unavailable"

        table = Table(
            title="Available formats:",
            title_justify="left",
            show_header=True,
            header_style=self._style_format_table,
            title_style=self._style_format_table_title,
        )
        table.add_column("ID", style=self._style_format_table, width=10)
        table.add_column("format note", width=20)
        table.add_column("resolution", width=20)

        for index, video in enumerate(content.video_format_list, start=1):
            table.add_row(
                Text(str(index)),
                Text(video.format_note, style=self._style_format_note),
                Text(video.resolution),
            )

        content_text = Text()

        if content.media_type == ContentMediaType.PLAYLIST:
            content_text.append(
                "Playlist information:\n",
                style=self._style_format_block,
            )
            content_text.append(
                "Number of videos to download: ",
                style=self._style_format_block_green_yellow,
            )
            content_text.append(
                f"{content.playlist_count}\n",
                style=self._style_text,
            )

        if content.media_type == ContentMediaType.VIDEO:
            content_text.append(
                "Video information:\n",
                style=self._style_format_block,
            )
            content_text.append(
                "Video title: ",
                style=self._style_format_block_green_yellow,
            )
            content_text.append(
                f"{content.title_video or unavailable_status}\n",
                style=self._style_text,
            )

        content_text.append(
            "Channel: ",
            style=self._style_format_block_green_yellow,
        )
        content_text.append(
            f"{content.channel}\n",
            style=self._style_text,
        )

        self._console.print(content_text)
        self._console.print(table)

        default_video_id: int = len(content.video_format_list)
        choices_video_ids: list[str] = [
            str(idx)
            for idx, _ in enumerate(
                content.video_format_list,
                start=1,
            )
        ]
        selected_id: int = IntPrompt.ask(
            "Enter video ID",
            choices=choices_video_ids,
            default=default_video_id,
            case_sensitive=False,
        )

        return selected_id

    def request_directory_from_user(
        self,
        default_output_dir: str,
    ) -> str:
        """Prompts the user for an output directory and ensures it exists.

        If the path already exists and is a directory, it is accepted.
        If it doesn't exist, the method creates it.
        On errors (e.g., permission denied, invalid name),
        the user is prompted again.

        Args:
            default_output_dir (str): Default path to suggest to the user.

        Returns:
            str: Absolute path to the selected output directory.
        """
        while True:
            output_dir: str = Prompt.ask(
                "Enter output catalog",
                default=default_output_dir,
            ).strip()

            if not output_dir:
                continue

            path_output_dir = pathlib.Path(output_dir)

            if path_output_dir.exists():
                break
            try:
                path_output_dir.mkdir(parents=True, exist_ok=True)
                break
            except (PermissionError, OSError, FileExistsError):
                path_error_msg: str = (
                    f"Failed to create directory: '{output_dir}'"
                )
                self._console.print(
                    path_error_msg,
                    style=self._style_error_text,
                )
                logger.exception(path_error_msg)
                continue

        return path_output_dir.as_posix()

    @contextmanager
    def show_spinner(
        self,
        message: str = "Loading",
        spinner: str = "shark",
        speed: float = 0.5,
    ) -> Generator:
        """Displays a Rich spinner animation during a long-running operation.

        Shows a non-blocking animated spinner with a custom message.
        Console output remains available inside the context.

        Args:
            message (str): Text to display next to the spinner..
            spinner (str): Name of the spinner animation.
            speed (float): Animation speed multiplier.
        """
        with self._console.status(message, spinner=spinner, speed=speed):
            yield

    @contextmanager
    def download_progress_bar(
        self,
        description: str = "Download",
        total: int = 100,
    ) -> Generator[tuple[Progress, TaskID]]:
        """Context manager for displaying a Rich progress bar.

        Provides a configured progress bar with description, bar, percentage.
        Yields a tuple of (progress instance, task ID) for updating.

        Args:
            description (str): Text shown before the progress bar.
            total (int): Total number of steps for the progress bar.

        Yields:
        tuple[Progress, TaskID]: A progress instance and its associated task ID
        """
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self._console,
        ) as progress:
            task_id: TaskID = progress.add_task(description, total=total)
            try:
                yield progress, task_id
            finally:
                progress.remove_task(task_id)
