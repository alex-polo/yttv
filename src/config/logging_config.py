from pathlib import Path

from .classes import LoggerConfig


def get_logging_config_dictionary(logger_config: LoggerConfig) -> dict:
    """Get logging configuration in dictConfig format.

    Args:
        logger_config: Logging configuration instance.

    Returns:
        Dict: Configuration for logging.config.dictConfig.

    Raises:
        ValueError: If configuration is invalid.
    """
    if not logger_config.logs_catalog or not logger_config.filename:
        value_error_msg: str = "Log catalog name and filename cannot be empty"
        raise ValueError(value_error_msg)

    logging_config: dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # noqa: E501
            },
            "detailed": {
                "format": (
                    "%(asctime)s - [%(levelname)s] - %(name)s - "
                    "(%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
                ),
            },
            "rich": {
                "format": "%(message)s",
            },
        },
        "handlers": {
            "log_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": Path(logger_config.logs_catalog) / logger_config.filename,
                "maxBytes": logger_config.max_bytes_size_file_log,
                "backupCount": logger_config.log_backup_count,
                "level": logger_config.log_level,
            },
        },
        "loggers": {
            "": {
                "handlers": ["log_file"],
                "level": logger_config.log_level,
                "propagate": False,
            },
        },
    }

    return logging_config
