from pathlib import Path
from typing import Any
from unittest.mock import (
    _patch,
    mock_open,
    patch,
)

import pytest

from src.config.classes import BaseConfiguration, ProjectInfo, ProjectSettings
from src.config.exceptions import (
    ConfigFieldValueNotSetError,
    ConfigFileNotFoundError,
    ConfigSetupError,
    PermissionConfigDeniedError,
    ValidateFfmpegError,
    ValidateOutputCatalogError,
)


class TestBaseConfig:
    """test base configuration."""

    @pytest.mark.parametrize(
        (
            "path_exist_condition",
            "path_is_file_condition",
            "side_effect",
            "expected_exception",
            "config_data",
        ),
        [
            # Путь не существует
            (False, True, None, ConfigFileNotFoundError, None),
            # Путь существует, но не является файлом
            (True, False, None, ConfigFileNotFoundError, None),
            # Путь является файлом, но нет доступа
            (
                True,
                True,
                PermissionError(),
                PermissionConfigDeniedError,
                None,
            ),
            # Секция настроек не найдена в файле не найдена
            (
                True,
                True,
                None,
                ConfigSetupError,
                b"[project]\nname='test_sections'",
            ),
        ],
    )
    def test_load_from_toml_error_scenarios(  # noqa: PLR6301
        self,
        path_exist_condition: bool,
        path_is_file_condition: bool,
        side_effect: Exception | None,
        expected_exception: type[Exception],
        config_data: bytes | None,
    ) -> None:
        """Testing different configuration loading scenarios."""
        if side_effect is not None:
            open_patch: _patch[Any] = patch(
                "pathlib.Path.open",
                side_effect=side_effect,
            )
        elif config_data is not None:
            open_patch = patch(
                "pathlib.Path.open",
                mock_open(read_data=config_data),
            )
        else:
            open_patch = patch("pathlib.Path.open")

        with (
            patch("pathlib.Path.exists", return_value=path_exist_condition),
            patch("pathlib.Path.is_file", return_value=path_is_file_condition),
            open_patch,
            pytest.raises(expected_exception),
        ):
            BaseConfiguration.load_from_toml(
                "non_exist_toml_file.toml",
                key="non_existent_section",
            )

    def test_load_from_toml_success(self) -> None:  # noqa: PLR6301
        """Configuration loaded successfully."""
        config_data = b"[project]\nname='application'\nversion='1.0.0'"
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("pathlib.Path.open", mock_open(read_data=config_data)),
        ):
            result: dict[str, str] = BaseConfiguration.load_from_toml(
                "test.toml",
            )
            assert result["name"] == "application"
            assert result["version"] == "1.0.0"


class TestProjectInfo:
    """Tests for ProjectInfo class."""

    def test_load_project_info_success(self) -> None:  # noqa: PLR6301
        """Test successful project info loading."""
        project_data = {
            "name": "TestApp",
            "version": "1.0.0",
            "description": "Test application",
            "authors": [{"name": "Test Author"}],
        }

        with patch.object(
            BaseConfiguration,
            "load_from_toml",
            return_value=project_data,
        ):
            info: ProjectInfo = ProjectInfo.load_project_info("pyproject.toml")
            assert info.name == "TestApp"
            assert info.version == "1.0.0"
            assert info.description == "Test application"
            assert info.authors == [{"name": "Test Author"}]

    def test_load_project_info_defaults(self) -> None:  # noqa: PLR6301
        """Test project info loading with defaults."""
        project_data: dict = {}

        with patch.object(
            BaseConfiguration,
            "load_from_toml",
            return_value=project_data,
        ):
            info: ProjectInfo = ProjectInfo.load_project_info("pyproject.toml")
            assert info.name == "YTTV"
            assert info.version == "unknown"
            assert not info.description
            assert not info.authors


class TestProjectSettings:
    """Tests for ProjectSettings class."""

    def test_load_project_settings_success(self) -> None:  # noqa: PLR6301
        """Test successful settings loading."""
        settings_data: dict[str, str] = {
            "ffmpeg_path": "/usr/bin/ffmpeg",
            "output_dir": "downloaded",
        }

        with patch.object(
            BaseConfiguration,
            "load_from_toml",
            return_value=settings_data,
        ):
            settings: ProjectSettings = ProjectSettings.load_project_settings(
                "pyproject.toml",
            )
            downloaded_path: Path = Path("downloaded").absolute()
            assert str(settings.ffmpeg_path) == "/usr/bin/ffmpeg"
            assert settings.output_dir == downloaded_path

    def test_load_project_settings_missing_fields(self) -> None:  # noqa: PLR6301
        """Test loading settings with missing required fields."""
        settings_data: dict[str, None] = {
            "ffmpeg_path": None,
            "output_dir": None,
        }

        with (
            patch.object(
                BaseConfiguration,
                "load_from_toml",
                return_value=settings_data,
            ),
            pytest.raises(ConfigFieldValueNotSetError),
        ):
            ProjectSettings.load_project_settings("pyproject.toml")

    def test_ffmpeg_validator_file_not_found(self) -> None:  # noqa: PLR6301
        """Test ffmpeg validation when file not found."""
        with (
            patch("pathlib.Path.exists", return_value=False),
            pytest.raises(ValidateFfmpegError),
        ):
            ProjectSettings.validate_ffmpeg_executable_file(
                Path("./fake_ffmpeg"),
            )

    def test_ffmpeg_validator_not_executable(self) -> None:  # noqa: PLR6301
        """Test ffmpeg validation when file not executable."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("os.access", return_value=False),
            pytest.raises(ValidateFfmpegError),
        ):
            ProjectSettings.validate_ffmpeg_executable_file(
                Path("./fake/ffmpeg"),
            )

    def test_output_dir_validator_success(self) -> None:  # noqa: PLR6301
        """Test successful output directory validation."""
        test_path = Path("./test")
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
        ):
            result: Path = ProjectSettings.validate_output_dir(test_path)
            assert result == test_path.absolute()

    def test_output_dir_validator_cannot_create(self) -> None:  # noqa: PLR6301
        """Test output directory validation when cannot create."""
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir", side_effect=OSError()),
            pytest.raises(ValidateOutputCatalogError),
        ):
            ProjectSettings.validate_output_dir(Path("./fake_dir/"))
