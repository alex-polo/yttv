from typing import Protocol

from src.config.classes import ProjectInfo, ProjectSettings


class ConfigFactory(Protocol):
    """Protocol defining the interface for configuration object creation.

    Implementations of this protocol are responsible for providing
    application configuration objects such as project metadata and settings.
    """

    def create_project_info(self) -> ProjectInfo:
        """Create and return the project metadata object.

        Returns:
            An instance of ProjectInfo.
        """
        ...

    def create_project_settings(self) -> ProjectSettings:
        """Create and return the project settings.

        Returns:
            An instance of ProjectSettings containing configurable parameters.
        """
        ...


class DefaultConfigFactory(ConfigFactory):
    """Default implementation of the ConfigFactory protocol."""

    def create_project_info(self) -> ProjectInfo:
        """Create a ProjectInfo instance by loading static project metadata.

        Returns:
            Initialized ProjectInfo object containing immutable
            project data.
        """
        return ProjectInfo.load_project_info()

    def create_project_settings(self) -> ProjectSettings:
        """Create a ProjectSettings instance by loading runtime configuration.

        Returns:
            Initialized ProjectSettings object containing immutable
            project settings.
        """
        return ProjectSettings.load_project_settings()
