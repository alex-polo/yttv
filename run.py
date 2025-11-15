import logging
import logging.config
import sys
from pathlib import Path

from src.config import LoggerConfig, get_logging_config_dictionary
from src.config.exceptions import ConfigSetupError
from src.main import main as app_run

logger: logging.Logger = logging.getLogger(__name__)


def setup_logging(config_path: str = "pyproject.toml") -> None:
    """Setup application logging.

    Args:
        config_path: Path to configuration file. Defaults to "pyproject.toml".

    Raises:
        ConfigSetupError: Error setting up logging.
    """
    try:
        logger_config: LoggerConfig = LoggerConfig.load_logging_config(
            config_path=config_path,
        )

        logs_dir = Path(logger_config.logs_catalog)
        logs_dir.mkdir(parents=True, exist_ok=True)

        logger_config_dictionary: dict = get_logging_config_dictionary(
            logger_config=logger_config,
        )

        logging.config.dictConfig(config=logger_config_dictionary)
    except Exception as e:
        error_msg: str = f"Error setting up logging: {e}"
        raise ConfigSetupError(error_msg) from e


def main() -> None:
    """Main entry point."""
    try:
        setup_logging()
        app_run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
        sys.exit(0)
    except Exception:
        exc_msg: str = "Critical application error."
        logger.exception(exc_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
