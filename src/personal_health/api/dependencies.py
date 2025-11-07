"""FastAPI dependency injection for shared resources."""

import os
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from personal_health.db import Database, UserProfileRepository
from personal_health.logging_config import get_logger

logger = get_logger(__name__)


AUTH_SECRET_KEY = "AUTH_SECRET"
AUTH_SECRET = os.getenv(AUTH_SECRET_KEY, "").strip()

# Global instances (initialized once by init_dependencies)
_db: Database | None = None
_user_profile_repo: UserProfileRepository | None = None


def init_dependencies(db_path: str) -> None:
    """Initialize global dependencies.

    Called once during application startup by create_app().

    Args:
        db_path (str): Path to the database file.
    """
    global _db, _user_profile_repo

    logger.info(f"Initializing database: {db_path}")

    _db = Database(db_path)
    _db.init()

    _user_profile_repo = UserProfileRepository(_db)
    logger.info("Dependencies initialized")


def get_db() -> Database:
    """FastAPI dependency to get the Database instance.

    Returns:
        Database: Configured database instance.

    Raises:
        RuntimeError: If dependencies not initialized.
    """
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_dependencies() first.")
    return _db


def get_user_profile_repo() -> UserProfileRepository:
    """FastAPI dependency to get the UserProfileRepository instance.

    Returns:
        UserProfileRepository: User profile repository instance.

    Raises:
        RuntimeError: If dependencies not initialized.
    """
    if _user_profile_repo is None:
        raise RuntimeError("UserProfileRepository not initialized. Call init_dependencies() first.")
    return _user_profile_repo


def simple_authentication(x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    """A simple authentication dependency to inspect a secret in request headers.

    Args:
        x_api_key (str): API key from X-API-Key header.

    Returns:
        str: The validated API key.

    Raises:
        HTTPException: 403 if authentication fails.
    """
    if not AUTH_SECRET:
        logger.error("AUTH_SECRET not configured - authentication disabled")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )

    if not x_api_key:
        logger.warning("Missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API key",
        )

    if not secrets.compare_digest(x_api_key, AUTH_SECRET):
        logger.warning("Failed authentication attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    logger.debug("Successful authentication with X-API-Key")
    return x_api_key


# Type aliases for dependency injection
DatabaseDep = Annotated[Database, Depends(get_db)]
UserProfileRepoDep = Annotated[UserProfileRepository, Depends(get_user_profile_repo)]
