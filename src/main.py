import logging
from typing import TYPE_CHECKING

from src.adapters import (
    YouTubeClientProtocol,
    YtDLPClientFactory,
)
from src.config.exceptions import ConfigSetupError
from src.config.factory import ConfigFactory, DefaultConfigFactory
from src.ui import RichUI
from src.workflow import PipelineWorkflow

if TYPE_CHECKING:
    from src.adapters.youtube_client import YtDLPClientAdapter

logger: logging.Logger = logging.getLogger(__name__)


class MainApp:
    """Main application class for YouTube downloader.

    Orchestrates the download workflow by initializing dependencies
    and executing the processing pipeline.
    """

    def __init__(
        self,
        config_factory: ConfigFactory,
        ui_interface: RichUI,
        youtube_adapter: YouTubeClientProtocol,
    ) -> None:
        """Initialize main application.

        Args:
            config_factory: Factory for creating configuration objects.
            ui_interface: User interface adapter for user interactions.
            youtube_adapter: YouTube client adapter for API operations.
        """
        self.config_factory: ConfigFactory = config_factory
        self.ui_interface: RichUI = ui_interface
        self.youtube_adapter: YouTubeClientProtocol = youtube_adapter

    def run(self) -> None:
        """Execute main application workflow.

        Creates and runs the processing workflow with all configured
        dependencies.
        """
        process_workflow: PipelineWorkflow = PipelineWorkflow(
            config_factory=self.config_factory,
            ui_interface=self.ui_interface,
            youtube_adapter=self.youtube_adapter,
        )

        process_workflow.execute()


def main() -> None:
    """Main entry point for YouTube downloader application."""
    try:
        factory = DefaultConfigFactory()
        ui = RichUI()
        youtube_adapter: YtDLPClientAdapter = YtDLPClientFactory(factory)

        main_app: MainApp = MainApp(
            config_factory=factory,
            ui_interface=ui,
            youtube_adapter=youtube_adapter,
        )

        main_app.run()
    except ConfigSetupError:
        logger.exception("Configuration setup failed")
