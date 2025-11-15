class ConfigSetupError(Exception):
    """Base exception for configuration setup errors."""


class ConfigFileNotFoundError(ConfigSetupError):
    """Exception raised when configuration file is not found."""


class PermissionConfigDeniedError(ConfigSetupError):
    """Exception raised when access to configuration file is denied."""


class InvalidConfigError(ConfigSetupError):
    """Exception raised when configuration in file is invalid."""


class ConfigFieldValueNotSetError(ConfigSetupError):
    """Exception raised when required configuration field is empty."""


class ValidateOutputCatalogError(ConfigSetupError):
    """Exception raised when output catalog for video files is incorrectly specified."""  # noqa: E501


class ValidateFfmpegError(ConfigSetupError):
    """Exception raised when ffmpeg is incorrectly specified."""
