"""FastAPI dependency injection for shared resources."""

import os
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from personal_health.api import oauth
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


def oauth_bearer_authentication(request: Request, authorization: str = Header(None)) -> str:
    """OAuth2 Bearer token authentication dependency.

    - HTTP requests (localhost): No authentication required
    - HTTPS requests: Requires OAuth Bearer token

    Args:
        request (Request): FastAPI request object.
        authorization (str): Authorization header value (e.g., "Bearer <token>").

    Returns:
        str: The client_id from the validated token, or empty string for HTTP.

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired on HTTPS.
    """
    # Skip authentication for HTTP (local development)
    if request.url.scheme == "http":
        logger.debug("HTTP request - skipping authentication")
        return ""

    # HTTPS - require OAuth Bearer token
    logger.debug("HTTPS request - OAuth authentication required")

    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid Authorization header format: {authorization}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Validate token
    is_valid, client_id = oauth.validate_access_token(token)
    if not is_valid or not client_id:
        logger.warning("Invalid or expired Bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"Successful OAuth authentication for client: {client_id}")
    return client_id


# Type aliases for dependency injection
DatabaseDep = Annotated[Database, Depends(get_db)]
UserProfileRepoDep = Annotated[UserProfileRepository, Depends(get_user_profile_repo)]
