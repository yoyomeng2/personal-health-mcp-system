"""OAuth2 authentication logic for MCP endpoints."""

import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Any

import jwt

from personal_health.logging_config import get_logger

logger = get_logger(__name__)

# OAuth2 Configuration
OAUTH_SECRET_KEY = os.getenv("OAUTH_SECRET_KEY", secrets.token_urlsafe(32))
OAUTH_ALGORITHM = "HS256"
OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Client credentials (in production, store these securely in database)
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "chatgpt-mcp-client")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "")

# In-memory storage for authorization codes
_auth_codes: dict[str, dict[str, Any]] = {}
_tokens: dict[str, dict[str, Any]] = {}
_registered_clients: dict[str, dict[str, Any]] = {}


def get_oauth_metadata(base_url: str) -> dict[str, Any]:
    """Generate OAuth2 authorization server metadata.

    This is returned by /.well-known/oauth-authorization-server endpoint.

    Args:
        base_url (str): The base URL of the server (e.g., https://example.com).

    Returns:
        dict: OAuth2 metadata according to RFC 8414.
    """
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "registration_endpoint": f"{base_url}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        "code_challenge_methods_supported": ["S256", "plain"],
    }


def get_protected_resource_metadata(base_url: str) -> dict[str, Any]:
    """Generate OAuth2 protected resource metadata.

    This is returned by /.well-known/oauth-protected-resource endpoint.

    Args:
        base_url (str): The base URL of the server (e.g., https://example.com).

    Returns:
        dict: OAuth2 protected resource metadata according to RFC 8414.
    """
    return {
        "resource": base_url,
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "resource_signing_alg_values_supported": [OAUTH_ALGORITHM],
    }


def create_authorization_code(client_id: str, redirect_uri: str, scope: str = "") -> str:
    """Create an authorization code for OAuth2 flow.

    Args:
        client_id (str): OAuth2 client ID.
        redirect_uri (str): Redirect URI for the client.
        scope (str, optional): Requested scope.

    Returns:
        str: Generated authorization code.
    """
    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "created_at": time.time(),
        "used": False,
    }
    logger.info(f"Created authorization code for client: {client_id}")
    return code


def validate_authorization_code(
    code: str, client_id: str, redirect_uri: str
) -> tuple[bool, str | None]:
    """Validate an authorization code.

    Args:
        code (str): Authorization code to validate.
        client_id (str): Client ID that should match.
        redirect_uri (str): Redirect URI that should match.

    Returns:
        tuple: (is_valid, scope) - True if valid with scope, or (False, None).
    """
    if code not in _auth_codes:
        logger.warning(f"Invalid authorization code: {code}")
        return False, None

    auth_data = _auth_codes[code]

    # Check if already used
    if auth_data["used"]:
        logger.warning(f"Authorization code already used: {code}")
        return False, None

    # Check expiration (5 minutes)
    if time.time() - auth_data["created_at"] > 300:
        logger.warning(f"Authorization code expired: {code}")
        del _auth_codes[code]
        return False, None

    # Validate client_id and redirect_uri
    if auth_data["client_id"] != client_id or auth_data["redirect_uri"] != redirect_uri:
        logger.warning(f"Authorization code validation failed for client: {client_id}")
        return False, None

    # Mark as used
    auth_data["used"] = True
    scope = auth_data.get("scope", "")

    logger.info(f"Authorization code validated for client: {client_id}")
    return True, scope


def create_access_token(client_id: str, scope: str = "") -> str:
    """Create a JWT access token.

    Args:
        client_id (str): OAuth2 client ID.
        scope (str, optional): Token scope.

    Returns:
        str: JWT access token.
    """
    expires_at = datetime.utcnow() + timedelta(minutes=OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": client_id,
        "scope": scope,
        "exp": expires_at,
        "iat": datetime.utcnow(),
        "token_type": "Bearer",
    }

    token: str = jwt.encode(payload, OAUTH_SECRET_KEY, algorithm=OAUTH_ALGORITHM)

    # Store token metadata
    _tokens[token] = {
        "client_id": client_id,
        "scope": scope,
        "created_at": time.time(),
    }

    logger.info(f"Created access token for client: {client_id}")
    return token


def validate_access_token(token: str) -> tuple[bool, str | None]:
    """Validate a JWT access token.

    Args:
        token (str): JWT access token to validate.

    Returns:
        tuple: (is_valid, client_id) - True if valid with client_id, or (False, None).
    """
    try:
        payload = jwt.decode(token, OAUTH_SECRET_KEY, algorithms=[OAUTH_ALGORITHM])
        client_id = payload.get("sub")

        if not client_id:
            logger.warning("Token missing 'sub' claim")
            return False, None

        logger.debug(f"Access token validated for client: {client_id}")
        return True, client_id

    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT validation failed: {e}")
        return False, None


def validate_client_credentials(client_id: str, client_secret: str) -> bool:
    """Validate OAuth2 client credentials.

    Args:
        client_id (str): Client ID.
        client_secret (str): Client secret.

    Returns:
        bool: True if credentials are valid.
    """
    # Check static client credentials
    if client_id == OAUTH_CLIENT_ID and secrets.compare_digest(client_secret, OAUTH_CLIENT_SECRET):
        logger.debug(f"Client credentials validated (static): {client_id=}")
        return True

    # Check registered clients
    client = _registered_clients.get(client_id)
    if client and secrets.compare_digest(client_secret, client["client_secret"]):
        logger.debug(f"Client credentials validated (registered): {client_id=}")
        return True

    logger.warning(f"Invalid client credentials for: {client_id=}")
    return False


def cleanup_expired_codes() -> None:
    """Remove expired authorization codes from storage."""
    current_time = time.time()
    expired_codes = [
        code for code, data in _auth_codes.items() if current_time - data["created_at"] > 300
    ]

    for code in expired_codes:
        del _auth_codes[code]

    if expired_codes:
        logger.info(f"Cleaned up {len(expired_codes)} expired authorization codes")


def register_client(
    client_name: str, redirect_uris: list[str], grant_types: list[str]
) -> dict[str, Any]:
    """Register a new OAuth client.

    Args:
        client_name (str): Name of the client application.
        redirect_uris (list[str]): List of allowed redirect URIs.
        grant_types (list[str]): List of allowed grant types.

    Returns:
        dict[str, Any]: Client registration response with client_id and client_secret.
    """
    # Generate client credentials
    client_id = secrets.token_urlsafe(32)
    client_secret = secrets.token_urlsafe(32)

    # Store client information
    _registered_clients[client_id] = {
        "client_name": client_name,
        "client_secret": client_secret,
        "redirect_uris": redirect_uris,
        "grant_types": grant_types,
        "created_at": time.time(),
    }

    logger.info(f"Registered new OAuth client: {client_name} (client_id: {client_id[:8]}...)")

    # Return RFC 7591 compliant response
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "grant_types": grant_types,
    }


def get_registered_client(client_id: str) -> dict[str, Any] | None:
    """Get registered client information.

    Args:
        client_id (str): Client ID to retrieve.

    Returns:
        dict[str, Any] | None: Client data if found, None otherwise.
    """
    return _registered_clients.get(client_id)
