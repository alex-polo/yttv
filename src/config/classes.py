import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.exceptions import (
    ConfigFieldValueNotSetError,
    ConfigFileNotFoundError,
    ConfigSetupError,
    PermissionConfigDeniedError,
    ValidateFfmpegError,
    ValidateOutputCatalogError,
)


class BaseConfiguration(BaseSettings):
    """Base configuraation class."""

    @staticmethod
    def load_from_toml(config_path: str, key: str = "project") -> dict:
        """Load project data from a TOML file.

        Args:
            config_path: Path to the project configuration file.
            key: Configuration section, defaults to "project".

        Returns:
            dict: A dictionary containing the configuration.

        Raises:
            ConfigFileNotFoundError: If the configuration file is not found
                or if the specified path is not a file.
            ConfigSetupError: If the specified key section is not found
                in the configuration file.
            PermissionConfigDeniedError: Insufficient permissions to
                access the configuration file.
        """
        path: Path = Path(config_path).resolve()

        if not path.exists():
            file_not_found_msg: str = (
                f"Configuration file not found: '{config_path}', "
                f"current directory: '{Path.cwd()}'"
            )
            raise ConfigFileNotFoundError(file_not_found_msg)

        if not path.is_file():
            not_a_file_msg: str = f"Path: '{config_path}' is not a file"
            raise ConfigFileNotFoundError(not_a_file_msg)

        try:
            with path.open("rb") as config_file:
                config_data: dict = tomllib.load(config_file)
        except PermissionError as e:
            permission_msg: str = f"Permission error: '{config_path}'"
            raise PermissionConfigDeniedError(permission_msg) from e

        project_data: dict | None = config_data.get(key)

        if not project_data:
            config_setup_error_msg: str = (
                f"Section: '{key}' not found in config file: {config_path}"
            )
            raise ConfigSetupError(config_setup_error_msg)

        return project_data

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        str_strip_whitespace=True,
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )


class ProjectInfo(BaseConfiguration):
    """Project information loaded from pyproject.toml."""

    name: str = Field(min_length=1, max_length=28, default="YTTV")
    version: str = Field(min_length=1, max_length=10, default="unknown")
    description: str = Field(min_length=0, max_length=108, default="")
    authors: list[dict] = Field(default_factory=list)

    @classmethod
    def load_project_info(
        cls,
        config_path: str = "pyproject.toml",
        key: str = "project",
    ) -> "ProjectInfo":
        """Load project information from pyproject.toml file.

        Args:
            config_path (str): Path to pyproject.toml file.
                               Defaults to "pyproject.toml"
            key: Name configuration section, Defaults "settings"

        Returns:
            ProjectInfo: Project information instance
        """
        project_data: dict = cls.load_from_toml(
            config_path=config_path,
            key=key,
        )

        return cls(
            name=project_data.get("name", "YTTV"),
            version=project_data.get("version", "unknown"),
            description=project_data.get("description", ""),
            authors=project_data.get("authors", []),
        )


class ProjectSettings(BaseConfiguration):
    """Project settings model with ffmpeg and output directory validation."""

    ffmpeg_path: Path
    output_dir: Path
    domains_youtube: set[str] = Field(default_factory=set)
    network_retries: int = Field(ge=1)
    network_socket_timeout: int = Field(ge=1)
    network_http_headers: dict[str, str]

    @field_validator("ffmpeg_path")
    @classmethod
    def validate_ffmpeg_executable_file(cls, path: Path) -> Path:
        """Validate that ffmpeg executable exists and is runnable.

        Args:
            path (Path): Path to ffmpeg executable

        Raises:
            ValidateFfmpegError: FFMPEG executable not found or not executable

        Returns:
            Path: Validated absolute path to ffmpeg executable
        """
        if not path.exists():
            error_msg: str = f"FFMPEG executable not found at: '{path}'"
            raise ValidateFfmpegError(error_msg)

        if not os.access(path, os.X_OK):
            os_not_access_error_msg: str = (
                f"FFMPEG is not executable: '{path}'"
            )
            raise ValidateFfmpegError(os_not_access_error_msg)

        return path.absolute()

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, path: Path) -> Path:
        """Validate and create output directory with proper permissions.

        Args:
            path (Path): Path to output directory

        Raises:
            ValidateOutputCatalogError: Cannot create directory or path
            is not a directory

        Returns:
            Path: Validated absolute path to output directory
        """
        if not path.exists():
            try:
                path.mkdir(exist_ok=True, parents=True)
            except OSError as e:
                error_msg: str = f"Cannot create output directory: '{path}'"
                raise ValidateOutputCatalogError(error_msg) from e

        if not path.is_dir():
            path_not_dir_error_msg: str = f"Path must be a directory: '{path}'"
            raise ValidateOutputCatalogError(path_not_dir_error_msg)

        return path.absolute()

    @classmethod
    def load_project_settings(
        cls,
        config_path: str = "pyproject.toml",
        key: str = "settings",
    ) -> "ProjectSettings":
        """Load and validate project settings from TOML configuration.

        Args:
            config_path (str): Path to TOML configuration file.
                               Defaults to "pyproject.toml"
            key: Name configuration section, Defaults "settings"

        Raises:
            ConfigFieldValueNotSetError: Required ffmpeg_path or output_dir
            not configured

        Returns:
            ProjectSettings: Validated project configuration instance
        """
        settings: dict = cls.load_from_toml(config_path, key=key)

        ffmpeg_path: str | None = settings.get("ffmpeg_path")
        output_dir: str | None = settings.get("output_dir")
        domains_youtube: set[str] = set(settings.get("domains_youtube", []))

        network_retries: int = settings.get("network_retries", 1)
        network_socket_timeout: int = settings.get("network_socket_timeout", 1)
        http_headers: str = settings.get("network_http_headers", "")
        network_http_headers: dict[str, str] = {"User-Agent": http_headers}

        if ffmpeg_path is None:
            error_msg: str = (
                f"Required field 'ffmpeg_path' not found in {config_path}"
            )
            raise ConfigFieldValueNotSetError(error_msg)

        if output_dir is None:
            output_dir_error_msg: str = (
                f"Required field 'output_dir' not found in {config_path}"
            )
            raise ConfigFieldValueNotSetError(output_dir_error_msg)

        return cls(
            ffmpeg_path=Path(ffmpeg_path),
            output_dir=Path(output_dir),
            domains_youtube=domains_youtube,
            network_retries=network_retries,
            network_socket_timeout=network_socket_timeout,
            network_http_headers=network_http_headers,
        )


class LoggerConfig(BaseConfiguration):
    """Application logging configuration."""

    filename: str = Field(min_length=1, max_length=108, default="yttv.log")
    logs_catalog: str = Field(min_length=1, max_length=108, default="logs")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = (
        "DEBUG"
    )
    log_backup_count: int = Field(ge=0, le=30, default=0)
    log_mb: int = Field(ge=1, le=100, default=10)

    @property
    def max_bytes_size_file_log(self) -> int:
        """Maximum log file size in bytes.

        Returns:
            int: Size in bytes (log_mb * 1024 * 1024)
        """
        return self.log_mb * 1024 * 1024

    @classmethod
    def load_logging_config(
        cls,
        config_path: str = "pyproject.toml",
    ) -> "LoggerConfig":
        """Load logging configuration from TOML file.

        Args:
            config_path (str): Path to TOML configuration file.
            Defaults to "pyproject.toml"

        Returns:
            LoggerConfig: Logging configuration instance
        """
        logging_data: dict = cls.load_from_toml(
            config_path=config_path,
            key="logging",
        )

        return cls(
            filename=logging_data.get("filename", "yttv.log"),
            logs_catalog=logging_data.get("logs_catalog", "logs"),
            log_level=logging_data.get("log_level", "DEBUG"),
            log_backup_count=logging_data.get("log_backup_count", 5),
            log_mb=logging_data.get("log_mb", 10),
        )
