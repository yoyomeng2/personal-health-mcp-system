"""Centralized logging configuration for Personal Health MCP System.

This module is intentionally named `logging_config` to avoid shadowing
the Python standard library `logging` package when imported from the
`personal_health` package.
"""

import logging
import logging.config
from pathlib import Path

from personal_health.config import Config


def setup_logging(config_path: Path | str | None = None, level: str | None = None) -> None:
    """Initialize logging configuration.

    Args:
        config_path: Path to logging config file. If None, uses defaults.
        level: Optional log level override (DEBUG, INFO, WARNING, ERROR).
    """
    if config_path is None:
        config_path = (
            Path(__file__).resolve().parent.parent.parent / "configs" / "personal_health.yaml"
        )

    if isinstance(config_path, str):
        config_path = Path(config_path)

    try:
        config = Config()

        log_level = level or config.get("logging.level", "INFO")

        # log_level = level or config_dict.get("logging", {}).get("level", "INFO")

        log_config: dict = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": config.get("logging", {}).get(
                        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    ),
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "standard",
                },
            },
            "root": {
                "level": log_level,
                "handlers": ["console"],
            },
            "loggers": {
                # to avoid 3rd party debug logs
                "httpcore": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "matplotlib.font_manager": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "openai._base_client": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "python_multipart.multipart": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "sse_starlette.sse": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
        }

        # Add file handler if log file is specified
        # Has been helpful for looking back at old logs
        log_file = config.get("logging", {}).get("file")
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handlers: dict = log_config["handlers"]
            handlers["file"] = {
                "class": "logging.FileHandler",
                "level": log_level,
                "filename": str(log_file),
                "formatter": "standard",
            }
            root_handlers: list = log_config["root"]["handlers"]
            root_handlers.append("file")

        logging.config.dictConfig(log_config)

        # Log confirmation that logging is configured (only visible if DEBUG enabled)
        logger = logging.getLogger(__name__)
        logger.debug(f"Logging configured: level={log_level}, config={config_path}")

    except FileNotFoundError:
        # Fallback to basic config if config file not found
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
