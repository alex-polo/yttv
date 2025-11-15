import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from src.adapters.youtube_client import YouTubeClientProtocol
from src.config.factory import ConfigFactory
from src.ui import RichUI
from src.workflow_steps import (
    BaseStep,
    DownloadVideoStep,
    FinishStep,
    GetURLStep,
    RequestFormatsByURLStep,
    RequiredDirectoryFromUserStep,
    RequiredFormatFromUserStep,
    ShowGreetingStep,
)

if TYPE_CHECKING:
    from src.config.classes import ProjectInfo, ProjectSettings

logger: logging.Logger = logging.getLogger(__name__)


class BaseWorkflow(ABC):
    """Base class for all processing workflows.

    Provides a template method pattern for executing workflows
    with configurable dependencies and execution hooks.
    """

    def __init__(
        self,
        ui_interface: RichUI,
        config_factory: ConfigFactory,
        youtube_adapter: YouTubeClientProtocol,
        **options: object,
    ) -> None:
        """Initialize workflow with dependencies.

        Args:
            ui_interface: User interface adapter.
            config_factory: Factory for creating configuration objects.
            youtube_adapter: YouTube client adapter for API operations.
            **options: Additional keyword arguments for extensibility.
        """
        self.ui_interface: RichUI = ui_interface
        self.config_factory: ConfigFactory = config_factory
        self.youtube_adapter: YouTubeClientProtocol = youtube_adapter
        self.options: dict[str, object] = options

    def execute(self) -> bool:
        """Execute the workflow using template method pattern.

        Returns:
            bool: True if workflow completed successfully, False otherwise.
        """
        try:
            context: dict[str, Any] = {}
            self._before_execute(context)
            result: bool = self._run(context)
            self._after_execute(context)
        except Exception:
            logger.exception("Workflow pipeline error.")
            return False
        else:
            return result

    @abstractmethod
    def _run(self, context: dict[str, Any]) -> bool:
        """Execute the main workflow logic.

        This method must be implemented by concrete workflow classes.

        Args:
            context: Shared context dictionary for passing data
                between workflow steps.

        Returns:
            bool: True if workflow completed successfully, False otherwise.
        """

    @abstractmethod
    def _before_execute(self, context: dict[str, Any]) -> None:
        """Hook executed before the main workflow logic.

        Can be overridden by subclasses to perform setup operations.

        Args:
            context: Shared context dictionary.
        """

    @abstractmethod
    def _after_execute(self, context: dict[str, Any]) -> None:
        """Hook executed after the main workflow logic.

        Can be overridden by subclasses to perform cleanup operations.

        Args:
            context: Shared context dictionary.
        """


class PipelineWorkflow(BaseWorkflow):
    """Concrete workflow implementation for downloading YouTube videos.

    Orchestrates a sequence of user-interactive and processing steps.
    """

    def _run(self, context: dict[str, Any]) -> bool:
        project_info: ProjectInfo = self.config_factory.create_project_info()
        project_settings: ProjectSettings = (
            self.config_factory.create_project_settings()
        )

        context["output_dir"] = project_settings.output_dir

        steps: list[BaseStep] = [
            ShowGreetingStep(
                ui=self.ui_interface,
                project_info=project_info,
            ),
            GetURLStep(
                ui=self.ui_interface,
                project_settings=project_settings,
            ),
            RequestFormatsByURLStep(
                ui=self.ui_interface,
                youtube_adapter=self.youtube_adapter,
            ),
            RequiredFormatFromUserStep(ui=self.ui_interface),
            RequiredDirectoryFromUserStep(ui=self.ui_interface),
            DownloadVideoStep(
                ui=self.ui_interface,
                youtube_adapter=self.youtube_adapter,
            ),
            FinishStep(ui=self.ui_interface),
        ]

        return all(step.execute(context) for step in steps)

    def _before_execute(self, context: dict[str, Any]) -> None:
        pass

    def _after_execute(self, context: dict[str, Any]) -> None:
        pass
