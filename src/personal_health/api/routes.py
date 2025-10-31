"""MCP routes - HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from personal_health.api.analysis import compute_summary
from personal_health.api.operation_ids import OperationId
from personal_health.api.schemas import (
    CorrelationResponse,
    EntriesResponse,
    Entry,
    EntryCreate,
    EntryResponse,
    EntryUpdate,
    PredictionResponse,
    SummaryResponse,
)
from personal_health.db import Database
from personal_health.exceptions import DatabaseError, DuplicateEntryError
from personal_health.logging_config import get_logger
from personal_health.ml import HealthPredictor
from personal_health.utils import generate_entry_id

logger = get_logger(__name__)
router = APIRouter()
db = Database()


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


@router.post("/add_entry", operation_id=OperationId.ADD_ENTRY, response_model=EntryResponse)
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


@router.put("/update_entry", operation_id=OperationId.UPDATE_ENTRY, response_model=EntryResponse)
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

        # Build update query for provided fields only
        update_fields = []
        params: list[str | int | float] = []
        if entry.date is not None:
            update_fields.append("date = ?")
            params.append(entry.date)
        if entry.meal is not None:
            update_fields.append("meal = ?")
            params.append(entry.meal)
        if entry.alcohol is not None:
            update_fields.append("alcohol = ?")
            params.append(entry.alcohol)
        if entry.stress is not None:
            update_fields.append("stress = ?")
            params.append(entry.stress)
        if entry.sleep_hours is not None:
            update_fields.append("sleep_hours = ?")
            params.append(entry.sleep_hours)
        if entry.pain_level is not None:
            update_fields.append("pain_level = ?")
            params.append(entry.pain_level)
        if entry.notes is not None:
            update_fields.append("notes = ?")
            params.append(entry.notes)

        if not update_fields:
            # No fields to update, return existing ID
            return EntryResponse(status="ok", entry_id=entry.id)

        # Execute update
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


@router.get("/get_entries", operation_id=OperationId.GET_ENTRIES, response_model=EntriesResponse)
async def get_entries(
    limit: int = 10,
    offset: int = 0,
    start_date: str | None = None,
    end_date: str | None = None,
) -> EntriesResponse:
    """Get recent health entries with optional date range filtering.

    Args:
        limit: Number of entries to return.
        offset: Number of entries to skip.
        start_date: Filter entries on or after this date (YYYY-MM-DD format, optional).
        end_date: Filter entries on or before this date (YYYY-MM-DD format, optional).

    Returns:
        List of entries.

    Raises:
        HTTPException: If query fails or date format invalid.
    """
    try:
        logger.debug(f"get_entries params: {limit=} {offset=} {start_date=} {end_date=}")

        # Validate date formats if provided
        from datetime import datetime

        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_date format. Expected YYYY-MM-DD, got: {start_date}",
                ) from None

        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date format. Expected YYYY-MM-DD, got: {end_date}",
                ) from None

        # Build dynamic query with optional date filters
        query = "SELECT * FROM entries"
        where_clauses = []
        params: list[str | int] = [limit, offset]

        if start_date:
            where_clauses.append("date >= ?")
            params.insert(0, start_date)
        if end_date:
            where_clauses.append("date <= ?")
            # Insert after start_date if present, otherwise at beginning
            params.insert(1 if start_date else 0, end_date)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY date DESC LIMIT ? OFFSET ?"

        rows = db.execute(query, tuple(params))
        entries = [
            Entry(
                id=r[0],
                date=r[1],
                meal=r[2],
                alcohol=r[3],
                stress=r[4],
                sleep_hours=r[5],
                pain_level=r[6],
                notes=r[7],
                created_at=r[8],
            )
            for r in rows
        ]
        logger.debug(f"get_entries {len(entries)=}")
        return EntriesResponse(count=len(entries), entries=entries)
    except DatabaseError as e:
        logger.error(f"Failed to retrieve entries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve entries") from e


@router.get("/get_entry/{entry_id}", operation_id=OperationId.GET_ENTRY, response_model=Entry)
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

        row = rows[0]
        entry = Entry(
            id=row[0],
            date=row[1],
            meal=row[2],
            alcohol=row[3],
            stress=row[4],
            sleep_hours=row[5],
            pain_level=row[6],
            notes=row[7],
            created_at=row[8],
        )
        return entry

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Failed to get entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to get entry") from e


@router.post("/reset_database", operation_id=OperationId.RESET_DATABASE)
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
    "/summarize_recent", operation_id=OperationId.GET_SUMMARY, response_model=SummaryResponse
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
    "/predict_next_day", operation_id=OperationId.GET_PREDICTION, response_model=PredictionResponse
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
    operation_id=OperationId.ANALYZE_TRIGGERS,
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
