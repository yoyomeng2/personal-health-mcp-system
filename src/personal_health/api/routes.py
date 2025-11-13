"""MCP routes - HTTP endpoints."""

import base64
import json
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware

from personal_health.api import oauth
from personal_health.api.analysis import compute_summary
from personal_health.api.dependencies import (
    DatabaseDep,
    UserProfileRepoDep,
    require_oauth_authorization_code,
)
from personal_health.api.operation_ids import OperationId
from personal_health.api.schemas import (
    CorrelationResponse,
    EntriesResponse,
    Entry,
    EntryCreate,
    EntryResponse,
    EntryUpdate,
    ExtractionResponse,
    GetEntriesRequest,
    PredictionResponse,
    SummaryResponse,
    UserProfileRequest,
    UserProfileResponse,
)
from personal_health.db.schemas import EntrySchema, UserProfileSchema
from personal_health.exceptions import DatabaseError, DuplicateEntryError
from personal_health.logging_config import get_logger
from personal_health.ml import HealthPredictor
from personal_health.ml.feature_extraction import extract_features_from_meal
from personal_health.ml.providers.base import UserProfile
from personal_health.utils import generate_entry_id, get_agent_ux_guide_content

logger = get_logger(__name__)
router = APIRouter()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        body = await request.body()
        headers = dict(request.headers)
        if "authorization" in headers:
            headers["authorization"] = "REDACTED"

        logger.debug(
            f"[MIDDLEWARE] {request.method} {request.url.path} headers={headers} body={body[:500]!r}"
        )
        response = await call_next(request)
        return response


@router.get("/", tags=["health"])
async def root(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
) -> dict:
    """Root endpoint.

    Returns:
        Service status.
    """
    return {"status": "ok", "service": "personal-health-mcp", "version": "0.1.0"}


@router.get("/health", tags=["health"])
async def health_check(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
) -> dict:
    """Health check endpoint.

    Returns:
        Health status.
    """
    return {"status": "healthy"}


# OAuth2 Discovery Endpoints
@router.get("/.well-known/oauth-authorization-server", tags=["oauth"])
async def oauth_authorization_server_metadata(request: Request) -> dict:
    """OAuth2 Authorization Server Metadata (RFC 8514).

    ChatGPT uses this to discover OAuth endpoints.

    Returns:
        OAuth2 server metadata.
    """
    base_url = str(request.base_url).rstrip("/")
    logger.info(f"OAuth metadata requested, base_url: {base_url}")
    return oauth.get_oauth_metadata(base_url)


@router.get("/.well-known/oauth-protected-resource", tags=["oauth"])
async def oauth_protected_resource_metadata(request: Request) -> dict:
    """OAuth2 Protected Resource Metadata.

    Indicates this resource requires OAuth2 Bearer tokens.

    Returns:
        OAuth2 protected resource metadata.
    """
    base_url = str(request.base_url).rstrip("/")
    logger.info(f"OAuth protected resource metadata requested, base_url: {base_url}")
    return oauth.get_protected_resource_metadata(base_url)


@router.get("/.well-known/openid-configuration", tags=["oauth"])
async def openid_configuration(request: Request) -> dict:
    """OpenID Connect Discovery (alternative to OAuth2 metadata).

    Returns:
        OpenID Connect configuration.
    """
    base_url = str(request.base_url).rstrip("/")
    logger.info(f"OpenID configuration requested, base_url: {base_url}")
    return oauth.get_oauth_metadata(base_url)


# OAuth2 Flow Endpoints
@router.get("/oauth/authorize", tags=["oauth"], response_class=HTMLResponse)
async def oauth_authorize(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query("code"),
    scope: str = Query(""),
    state: str = Query(None),
) -> HTMLResponse:
    """OAuth2 authorization endpoint.

    In production, this would show a consent screen. For now, auto-approve.

    Args:
        client_id (str): OAuth2 client ID.
        redirect_uri (str): Redirect URI.
        response_type (str): Must be 'code'.
        scope (str): Requested scope.
        state (str, optional): CSRF protection state.

    Returns:
        HTML response with auto-redirect to redirect_uri with code.
    """
    logger.info(f"Authorization request from client: {client_id}")

    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only 'code' response_type supported")

    # Generate authorization code
    code = oauth.create_authorization_code(client_id, redirect_uri, scope)

    # Build redirect URL
    redirect_params = f"code={code}"
    if state:
        redirect_params += f"&state={state}"

    final_redirect = f"{redirect_uri}?{redirect_params}"

    # Auto-approve with redirect (in production, show consent form)
    html_content = f"""
    <html>
        <head>
            <title>Authorization</title>
            <meta http-equiv="refresh" content="0;url={final_redirect}">
        </head>
        <body>
            <p>Redirecting to {redirect_uri}...</p>
            <p>If not redirected, <a href="{final_redirect}">click here</a>.</p>
        </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@router.post("/oauth/token", tags=["oauth"])
async def oauth_token(
    request: Request,
    grant_type: str = Form(...),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    client_id: str = Form(None),
    client_secret: str = Form(None),
) -> dict:
    """OAuth2 token endpoint.

    Exchange authorization code for access token.

    Args:
        request (Request): The incoming HTTP request.
        grant_type (str): Must be 'authorization_code' or 'client_credentials'.
        code (str): Authorization code (for authorization_code grant).
        redirect_uri (str): Redirect URI (for authorization_code grant).
        client_id (str): OAuth2 client ID.
        client_secret (str): OAuth2 client secret.

    Returns:
        Token response with access_token.
    """

    # Extract client credentials from HTTP Basic Auth if present
    auth_header = request.headers.get("authorization") if request else None
    basic_client_id = basic_client_secret = None
    if auth_header:
        scheme, credentials = get_authorization_scheme_param(auth_header)
        if scheme.lower() == "basic" and credentials:
            try:
                decoded = base64.b64decode(credentials).decode()
                basic_client_id, basic_client_secret = decoded.split(":", 1)
            except Exception as e:
                logger.warning(f"Failed to decode HTTP Basic Auth: {e}")

    # Prefer HTTP Basic Auth, fallback to form fields
    effective_client_id = basic_client_id or client_id
    effective_client_secret = basic_client_secret or client_secret

    logger.info(f"Token request from client: {effective_client_id}, grant_type: {grant_type}")

    # Validate client credentials
    if not effective_client_id or not effective_client_secret:
        logger.warning(
            "/oauth/token: Missing client_id or client_secret (neither form nor HTTP Basic Auth provided)"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing client credentials"
        )
    if not oauth.validate_client_credentials(effective_client_id, effective_client_secret):
        logger.warning(
            f"/oauth/token: Invalid client credentials for client_id={effective_client_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client credentials"
        )

    if grant_type == "authorization_code":
        if not code or not redirect_uri:
            logger.warning(
                f"/oauth/token: Missing code or redirect_uri for authorization_code grant. code={code}, redirect_uri={redirect_uri}"
            )
            raise HTTPException(
                status_code=400,
                detail="code and redirect_uri required for authorization_code grant",
            )

        # Validate authorization code
        is_valid, scope = oauth.validate_authorization_code(code, effective_client_id, redirect_uri)
        if not is_valid:
            logger.warning(
                f"/oauth/token: Invalid authorization code. {code=}, client_id={effective_client_id}, {redirect_uri=}"
            )
            raise HTTPException(status_code=400, detail="Invalid authorization code")

        # Create access token
        access_token = oauth.create_access_token(effective_client_id, scope or "")

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": oauth.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "scope": scope or "",
        }

    elif grant_type == "client_credentials":
        # Direct token for client credentials flow
        access_token = oauth.create_access_token(effective_client_id, "")

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": oauth.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")


@router.post("/oauth/register", tags=["oauth"])
async def oauth_register(request: Request) -> dict:
    """OAuth2 Dynamic Client Registration (RFC 7591).

    Allows clients to register themselves and obtain client credentials.

    Request body (JSON):
        {
            "client_name": "My Client App",
            "redirect_uris": ["https://example.com/callback"],
            "grant_types": ["authorization_code"]
        }

    Returns:
        Client registration response with client_id and client_secret.
    """
    # Simple protection: limit total number of registered clients
    if len(oauth._registered_clients) >= 5:
        logger.warning(
            f"Registration limit reached. Client IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=429,
            detail="Maximum number of clients registered. Contact administrator.",
        )

    try:
        body = await request.json()
    except Exception:
        body = {}

    client_name = body.get("client_name", "unknown")
    redirect_uris = body.get("redirect_uris", [])
    grant_types = body.get("grant_types", ["authorization_code"])

    logger.info(
        f"Dynamic client registration request: {client_name} from {request.client.host if request.client else 'unknown'}"
    )

    # Register the client and return the registration response
    registration_response = oauth.register_client(
        client_name=client_name, redirect_uris=redirect_uris, grant_types=grant_types
    )

    return registration_response


@router.get(
    "/agent_ux_guide",
    operation_id=OperationId.GET_AGENT_UX_GUIDE.operation_id,
    response_model=dict,
    tags=["agent-documentation"],
)
async def get_agent_ux_guide(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
) -> dict:
    """**IMPORTANT: Call this FIRST when helping users with health tracking.**

    Get the agent UX guide that defines conversational patterns, workflows,
    and best practices for creating health entries. This guide contains:
    - Natural language interaction patterns
    - Profile-aware inference rules
    - Batch confirmation formats
    - Feature extraction workflows
    - Example dialogs

    Always retrieve this guide at the start of a health tracking conversation
    to ensure you follow the correct UX patterns.

    Returns:
        dict: Contains 'content' (markdown text) and 'version' fields.

    Raises:
        HTTPException: If guide file cannot be read.
    """
    try:
        logger.info("Retrieving agent UX guide")

        return {
            "content": get_agent_ux_guide_content(),
            "version": "0.1.0",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve agent UX guide: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agent UX guide") from e


@router.post(
    "/add_entry",
    operation_id=OperationId.ADD_ENTRY.operation_id,
    response_model=EntryResponse,
    tags=["entries"],
)
async def add_entry(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
    entry: EntryCreate,
    db: DatabaseDep,
) -> EntryResponse:
    """Add a new health entry.

    Entries are deduplicated via deterministic ID generation. If an entry already exists, returns existing entry_id.

    Args:
        entry (EntryCreate): Health entry data.
        db (DatabaseDep): Database dependency (injected).

    Returns:
        Response with entry ID (existing or newly created).

    Raises:
        HTTPException: If entry creation fails.
    """
    try:
        entries = [
            entry.date,
            entry.meal,
            entry.alcohol,
            entry.stress,
            entry.sleep_hours,
            entry.pain_level,
            entry.notes,
        ]
        # Generate deterministic ID from composite key fields
        entry_id = generate_entry_id(entries)

        # Attempt to insert with explicit ID
        try:
            db.execute(
                "INSERT INTO entries (id, date, meal, alcohol, stress, sleep_hours, pain_level, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (entry_id, *entries),
            )
            logger.info(f"Entry created: id={entry_id}")
        except DuplicateEntryError:
            logger.info(f"Entry already exists: id={entry_id} (idempotent response)")

        return EntryResponse(status="ok", entry_id=entry_id)
    except DatabaseError as e:
        logger.error(f"Failed to create entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to create entry") from e


@router.put(
    "/update_entry",
    operation_id=OperationId.UPDATE_ENTRY.operation_id,
    response_model=EntryResponse,
    tags=["entries"],
)
async def update_entry(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
    entry: EntryUpdate,
    db: DatabaseDep,
) -> EntryResponse:
    """Update an existing health entry.

    Only provided fields will be updated.

    Args:
        entry: Entry ID and fields to update.

    Returns:
        Response with entry ID.

    Raises:
        HTTPException: If entry not found, update fails, or results in duplicate.
    """
    try:
        # First, verify entry exists
        existing = db.execute("SELECT * FROM entries WHERE id = ?", (entry.id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Entry not found")

        # Build update query from provided fields only (exclude None values and id)
        update_data = entry.model_dump(exclude_none=True, exclude={"id"})

        if not update_data:
            # No fields to update, return existing ID
            return EntryResponse(status="ok", entry_id=entry.id)

        # Build SQL dynamically
        update_fields = [f"{field} = ?" for field in update_data.keys()]
        params = list(update_data.values())
        params.append(entry.id)  # For WHERE clause

        query = f"UPDATE entries SET {', '.join(update_fields)} WHERE id = ?"

        try:
            db.execute(query, tuple(params))
            logger.info(f"Entry updated: id={entry.id}")
            return EntryResponse(status="ok", entry_id=entry.id)
        except DuplicateEntryError:
            # Update would create duplicate (if composite key constraints existed)
            raise HTTPException(
                status_code=409, detail="Update would create duplicate entry"
            ) from None

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Failed to update entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to update entry") from e


@router.get(
    "/get_entries",
    response_model=EntriesResponse,
    operation_id=OperationId.GET_ENTRIES.operation_id,
    tags=["entries"],
)
async def get_entries(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
    db: DatabaseDep,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> EntriesResponse:
    """Get recent health entries with optional date range filtering."""
    try:
        params = GetEntriesRequest(
            limit=limit, offset=offset, start_date=start_date, end_date=end_date
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    query = "SELECT * FROM entries WHERE 1=1"
    query_params = []

    if params.start_date:
        query += " AND date >= ?"
        query_params.append(params.start_date)

    if params.end_date:
        query += " AND date <= ?"
        query_params.append(params.end_date)

    query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    query_params.extend([str(params.limit), str(params.offset)])

    with db.connect() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(query, tuple(query_params)).fetchall()

        entries = [Entry.model_validate(dict(r)) for r in rows]
        return EntriesResponse(count=len(entries), entries=entries)


@router.get(
    "/get_entry/{entry_id}",
    operation_id=OperationId.GET_ENTRY.operation_id,
    response_model=Entry,
    tags=["entries"],
)
async def get_entry(
    _: Annotated[str, Depends(require_oauth_authorization_code)], entry_id: str, db: DatabaseDep
) -> Entry:
    """Get a single health entry by ID.

    Args:
        entry_id: Entry ID (16-char hash).

    Returns:
        Entry: Entry data as Pydantic model.

    Raises:
        HTTPException: If entry not found or query fails.
    """
    try:
        rows = db.execute(
            "SELECT * FROM entries WHERE id = ?",
            (entry_id,),
        )

        if not rows:
            logger.warning(f"Entry not found: {entry_id}")
            raise HTTPException(status_code=404, detail="Entry not found")

        return Entry.model_validate(dict(rows[0]))

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Failed to get entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to get entry") from e


@router.post(
    "/entries/{entry_id}/extract_features",
    operation_id=OperationId.EXTRACT_FEATURES.operation_id,
    response_model=ExtractionResponse,
    tags=["entries"],
)
async def extract_features(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
    db: DatabaseDep,
    user_profile_repo: UserProfileRepoDep,
    entry_id: str,
    user_id: str = "default_user",
) -> ExtractionResponse:
    """Extract binary features from meal description using LLM.

    This endpoint uses the configured LLM provider to analyze the meal description
    and extract binary features (0/1/None) for dietary components like dairy, gluten, etc.
    It considers the user's profile for context-aware inference.

    Args:
        entry_id (str): Entry ID to extract features from.
        user_id (str, optional): User ID for profile context. Defaults to "default_user".

    Returns:
        ExtractionResponse: Extracted features with confidence and reasoning.

    Raises:
        HTTPException: If entry not found, profile issues, or extraction fails.
    """
    try:
        # Get the entry
        rows = db.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        if not rows:
            logger.warning(f"Entry not found for extraction: {entry_id}")
            raise HTTPException(status_code=404, detail="Entry not found")

        entry_dict = dict(rows[0])
        entry = EntrySchema.model_validate(entry_dict)

        # Get user profile
        db_profile = user_profile_repo.get(user_id)
        if not db_profile:
            logger.warning(f"User profile not found: {user_id}, using defaults")
            # Create default profile
            default_profile = UserProfileSchema(id=user_id, date_last_confirmed=None)
            user_profile_repo.create_or_update(default_profile)
            db_profile = user_profile_repo.get(user_id)

        if not db_profile:
            raise HTTPException(status_code=500, detail="Failed to create user profile")

        user_profile = UserProfile.from_db(db_profile)

        # Extract features using LLM
        logger.info(f"Extracting features for entry {entry_id} with user {user_id}")
        extracted = extract_features_from_meal(entry, user_profile)

        # Update entry with extracted features
        update_fields = []
        update_values: list[str] = []
        for feature_name, feature_value in extracted.features.items():
            if feature_value is not None:  # Only update non-null values
                update_fields.append(f"{feature_name} = ?")
                update_values.append(str(feature_value))

        if update_fields:
            update_query = f"UPDATE entries SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(entry_id)
            db.execute(update_query, tuple(update_values))
            logger.info(f"Updated {len(update_fields)} features for entry {entry_id}")

        # Return response
        return ExtractionResponse(
            entry_id=entry_id,
            features=extracted.features,
            confidence=extracted.confidence,
            reasoning=extracted.reasoning,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Configuration error during extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Configuration error: {e!s}") from e
    except Exception as e:
        logger.error(f"Failed to extract features: {e}")
        raise HTTPException(status_code=500, detail=f"Feature extraction failed: {e!s}") from e


@router.post(
    "/reset_database",
    operation_id=OperationId.RESET_DATABASE.operation_id,
    tags=["admin"],
)
async def reset_database(
    _: Annotated[str, Depends(require_oauth_authorization_code)], db: DatabaseDep
) -> dict:
    """Reset the database by deleting all entries.

    Returns:
        Success message.

    Raises:
        HTTPException: If reset fails.
    """
    try:
        db.execute("DELETE FROM entries")
        db.execute("DELETE FROM user_profile")
        logger.info("Database reset: all tables deleted")
        return {"status": "ok", "message": "Database reset successfully"}
    except DatabaseError as e:
        logger.error(f"Failed to reset database: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset database") from e


@router.get(
    "/summarize_recent",
    operation_id=OperationId.GET_SUMMARY.operation_id,
    response_model=SummaryResponse,
    tags=["analysis"],
)
async def summarize_recent(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
    db: DatabaseDep,
    window_days: int = 7,
) -> SummaryResponse:
    """Get summary of recent health data.

    Args:
        db (DatabaseDep): Database dependency (injected).
        window_days: Number of days to summarize.

    Returns:
        Summary statistics.

    Raises:
        HTTPException: If summary fails.
    """
    try:
        logger.info(f"Computing summary for {window_days} days")
        # Fetch all entries (summary will filter by date)
        rows = db.execute(
            "SELECT id, date, meal, alcohol, stress, sleep_hours, pain_level, notes, created_at FROM entries ORDER BY date DESC"
        )
        entries = [
            {
                "id": r[0],
                "date": r[1],
                "meal": r[2],
                "alcohol": r[3],
                "stress": r[4],
                "sleep_hours": r[5],
                "pain_level": r[6],
                "notes": r[7],
                "created_at": r[8],
            }
            for r in rows
        ]
        # Compute summary using analysis module
        summary = compute_summary(entries, window_days=window_days)
        return SummaryResponse(window_days=window_days, summary=summary)
    except Exception as e:
        logger.error(f"Failed to compute summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute summary") from e


def _get_predictor(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
) -> HealthPredictor:
    """Dependency to get and initialize the health predictor instance."""
    predictor = HealthPredictor()
    predictor.load()
    return predictor


_predict_next_day_predictor_dep = Depends(_get_predictor)


@router.get(
    "/predict_next_day",
    operation_id=OperationId.GET_PREDICTION.operation_id,
    response_model=PredictionResponse,
    tags=["analysis"],
)
async def predict_next_day(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
    db: DatabaseDep,
    date: str,
    predictor: HealthPredictor = _predict_next_day_predictor_dep,
) -> PredictionResponse:
    """Predict pain level for the day after the given date.

    Args:
        db (DatabaseDep): Database dependency (injected).
        date (str): Reference date in YYYY-MM-DD format. Prediction will be for the next day.
        predictor (HealthPredictor, optional): Injected HealthPredictor dependency.

    Returns:
        PredictionResponse: Prediction including the reference date, prediction date, predicted pain level, and confidence.

    Raises:
        HTTPException: If prediction fails or insufficient data (422 status).
    """
    try:
        logger.info(f"Computing pain prediction for {date}")

        # Make prediction using injected predictor
        result = predictor.predict(date, db)

        # Handle insufficient data (cold start)
        if result["prediction"] is None:
            status_msg = result.get("status", "Insufficient data")
            logger.warning(f"Cannot predict for {date}: {status_msg}")
            raise HTTPException(
                status_code=422,
                detail=f"Cannot predict: {status_msg}",
            )

        # Calculate the next day for clarity
        from datetime import datetime, timedelta

        reference_date = datetime.strptime(date, "%Y-%m-%d")
        prediction_date = reference_date + timedelta(days=1)

        return PredictionResponse(
            based_on_date=date,
            prediction_for_date=prediction_date.strftime("%Y-%m-%d"),
            predicted_pain_level=result["prediction"],
            confidence=result["confidence"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to predict: {e}")
        raise HTTPException(status_code=500, detail="Failed to predict") from e


@router.get(
    "/analyze_pain_triggers",
    operation_id=OperationId.ANALYZE_TRIGGERS.operation_id,
    response_model=CorrelationResponse,
    tags=["analysis"],
)
async def analyze_pain_triggers(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
) -> dict:
    """Analyze potential pain triggers from entries.

    Returns:
        Analysis of pain triggers.
    """
    try:
        logger.info("Analyzing pain triggers")
        return {"analysis": None}
    except Exception as e:
        logger.error(f"Failed to analyze pain triggers: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze pain triggers") from e


@router.get(
    "/user/profile",
    operation_id=OperationId.GET_USER_PROFILE.operation_id,
    response_model=UserProfileResponse,
    tags=["user-profile"],
)
async def get_user_profile(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
    user_profile_repo: UserProfileRepoDep,
    user_id: str = Query("default_user"),
) -> UserProfileResponse:
    """Get user dietary profile.

    Args:
        user_profile_repo (UserProfileRepoDep): User profile repository dependency (injected).
        user_id (str): User ID. Defaults to 'default_user'.

    Returns:
        User profile with dietary preferences and staleness check.

    Raises:
        HTTPException: If profile retrieval fails.
    """
    try:
        logger.info(f"Retrieving user profile: {user_id}")
        profile = user_profile_repo.get(user_id)

        if not profile:
            logger.info(f"Profile not found, creating default: {user_id}")

            default_profile = UserProfileSchema(id=user_id, date_last_confirmed=None)
            user_profile_repo.create_or_update(default_profile)
            profile = user_profile_repo.get(user_id)

        if not profile:
            raise DatabaseError("Failed to create default profile")

        # Parse JSON fields
        dietary_restrictions = json.loads(profile["dietary_restrictions"] or "[]")
        allergies = json.loads(profile["allergies"] or "[]")
        preferences = json.loads(profile["preferences"] or "{}")
        habits = json.loads(profile["habits"] or "{}")

        # Check if profile is stale
        profile_stale = user_profile_repo.is_stale(user_id)

        return UserProfileResponse(
            id=profile["id"],
            dietary_restrictions=dietary_restrictions,
            allergies=allergies,
            preferences=preferences,
            habits=habits,
            created_at=profile["created_at"],
            updated_at=profile["updated_at"],
            date_last_confirmed=profile["date_last_confirmed"],
            profile_stale=profile_stale,
        )
    except DatabaseError as e:
        logger.error(f"Failed to retrieve user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user profile") from e


@router.put(
    "/user/profile",
    operation_id=OperationId.UPDATE_USER_PROFILE.operation_id,
    response_model=UserProfileResponse,
    tags=["user-profile"],
)
async def update_user_profile(
    _: Annotated[str, Depends(require_oauth_authorization_code)],
    profile_data: UserProfileRequest,
    user_profile_repo: UserProfileRepoDep,
    user_id: str = Query("default_user"),
) -> UserProfileResponse:
    """Create or update user dietary profile.

    Args:
        profile_data: User profile data.
        user_profile_repo (UserProfileRepoDep): User profile repository dependency (injected).
        user_id (str): User ID. Defaults to 'default_user'.

    Returns:
        Updated user profile.

    Raises:
        HTTPException: If profile update fails.
    """
    try:
        logger.info(f"Updating user profile: {user_id}")

        # Convert to JSON for storage
        dietary_restrictions_json = json.dumps(profile_data.dietary_restrictions)
        allergies_json = json.dumps(profile_data.allergies)
        preferences_json = json.dumps(profile_data.preferences)
        habits_json = json.dumps(profile_data.habits)

        profile_schema = UserProfileSchema(
            id=user_id,
            dietary_restrictions=dietary_restrictions_json,
            allergies=allergies_json,
            preferences=preferences_json,
            habits=habits_json,
            date_last_confirmed=None,
        )

        user_profile_repo.create_or_update(profile_schema)

        # Retrieve updated profile
        profile = user_profile_repo.get(user_id)
        if not profile:
            raise DatabaseError("Failed to retrieve updated profile")

        profile_stale = user_profile_repo.is_stale(user_id)

        return UserProfileResponse(
            id=profile["id"],
            dietary_restrictions=profile_data.dietary_restrictions,
            allergies=profile_data.allergies,
            preferences=profile_data.preferences,
            habits=profile_data.habits,
            created_at=profile["created_at"],
            updated_at=profile["updated_at"],
            date_last_confirmed=profile["date_last_confirmed"],
            profile_stale=profile_stale,
        )
    except DatabaseError as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user profile") from e
