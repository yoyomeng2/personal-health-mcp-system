"""MCP routes - HTTP endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query

from personal_health.api.analysis import compute_summary
from personal_health.api.operation_ids import OperationId
from personal_health.api.schemas import (
    CorrelationResponse,
    EntriesResponse,
    Entry,
    EntryCreate,
    EntryResponse,
    EntryUpdate,
    GetEntriesRequest,
    PredictionResponse,
    SummaryResponse,
    UserProfileRequest,
    UserProfileResponse,
)
from personal_health.db import Database, UserProfileRepository
from personal_health.exceptions import DatabaseError, DuplicateEntryError
from personal_health.logging_config import get_logger
from personal_health.ml import HealthPredictor
from personal_health.utils import generate_entry_id

logger = get_logger(__name__)
router = APIRouter()
db = Database()
user_profile_repo = UserProfileRepository(db)


@router.get("/", tags=["health"])
async def root() -> dict:
    """Root endpoint.

    Returns:
        Service status.
    """
    logger.debug("root endpoint called")
    return {"status": "ok", "service": "personal-health-mcp", "version": "0.1.0"}


@router.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status.
    """
    logger.debug("health_check endpoint called")
    return {"status": "healthy"}


@router.post(
    "/add_entry", operation_id=OperationId.ADD_ENTRY.operation_id, response_model=EntryResponse
)
async def add_entry(entry: EntryCreate) -> EntryResponse:
    """Add a new health entry.

    Entries are deduplicated via deterministic ID generation. If an entry already exists, returns existing entry_id.

    Args:
        entry: Health entry data.

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

        logger.debug(f"insert_entry params: {entry.model_dump()}")

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
)
async def update_entry(entry: EntryUpdate) -> EntryResponse:
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
        logger.debug(f"update_entry params: {entry.model_dump()}")
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
)
async def get_entries(
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
        logger.debug(f"get_entries {len(entries)=}")
        return EntriesResponse(count=len(entries), entries=entries)


@router.get(
    "/get_entry/{entry_id}", operation_id=OperationId.GET_ENTRY.operation_id, response_model=Entry
)
async def get_entry(entry_id: str) -> Entry:
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


@router.post("/reset_database", operation_id=OperationId.RESET_DATABASE.operation_id)
async def reset_database() -> dict:
    """Reset the database by deleting all entries.

    Returns:
        Success message.

    Raises:
        HTTPException: If reset fails.
    """
    try:
        db.execute("DELETE FROM entries")
        logger.info("Database reset: all entries deleted")
        return {"status": "ok", "message": "Database reset successfully"}
    except DatabaseError as e:
        logger.error(f"Failed to reset database: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset database") from e


@router.get(
    "/summarize_recent",
    operation_id=OperationId.GET_SUMMARY.operation_id,
    response_model=SummaryResponse,
)
async def summarize_recent(window_days: int = 7) -> SummaryResponse:
    """Get summary of recent health data.

    Args:
        window_days: Number of days to summarize.

    Returns:
        Summary statistics.

    Raises:
        HTTPException: If summary fails.
    """
    try:
        logger.debug(f"summarize_recent params: {window_days=}")
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
        logger.debug(f"summarize_recent {len(entries)=}")
        # Compute summary using analysis module
        summary = compute_summary(entries, window_days=window_days)
        return SummaryResponse(window_days=window_days, summary=summary)
    except Exception as e:
        logger.error(f"Failed to compute summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute summary") from e


def _get_predictor() -> HealthPredictor:
    """Dependency to get and initialize the health predictor instance."""
    predictor = HealthPredictor()
    predictor.load()
    return predictor


_predict_next_day_predictor_dep = Depends(_get_predictor)


@router.get(
    "/predict_next_day",
    operation_id=OperationId.GET_PREDICTION.operation_id,
    response_model=PredictionResponse,
)
async def predict_next_day(
    date: str, predictor: HealthPredictor = _predict_next_day_predictor_dep
) -> PredictionResponse:
    """Predict pain level for the day after the given date.

    Args:
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
)
async def analyze_pain_triggers() -> dict:
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
async def get_user_profile(user_id: str = "default_user") -> UserProfileResponse:
    """Get user dietary profile.

    Args:
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
            user_profile_repo.create_or_update(user_id)
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
    profile_data: UserProfileRequest, user_id: str = "default_user"
) -> UserProfileResponse:
    """Create or update user dietary profile.

    Args:
        profile_data: User profile data.
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

        user_profile_repo.create_or_update(
            user_id=user_id,
            dietary_restrictions=dietary_restrictions_json,
            allergies=allergies_json,
            preferences=preferences_json,
            habits=habits_json,
        )

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
