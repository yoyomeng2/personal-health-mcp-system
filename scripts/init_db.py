"""Initialize database schema."""

from personal_health.db import Database
from personal_health.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    """Initialize database."""
    logger.info("Initializing database...")
    db = Database()
    db.init()
    logger.info("Database initialized successfully")


if __name__ == "__main__":
    main()
