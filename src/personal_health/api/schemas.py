"""MCP API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EntryBase(BaseModel):
    """Base schema with all entry fields (all optional)."""

    date: str | None = Field(None, description="Entry date in YYYY-MM-DD format")
    meal: str | None = Field(None, description="Meal description")
    alcohol: str | None = Field(None, description="Alcohol consumption")
    stress: int | None = Field(None, ge=0, le=10, description="Stress level (0-10)")
    sleep_hours: float | None = Field(None, ge=0, le=24, description="Sleep hours")
    pain_level: int | None = Field(None, ge=0, le=10, description="Pain level (0-10)")
    notes: str | None = Field(None, description="Additional notes")
    # Binary feature columns (0/1/null)
    has_beans: int | None = Field(None, ge=0, le=1, description="Has beans (0/1)")
    has_rice: int | None = Field(None, ge=0, le=1, description="Has rice (0/1)")
    has_pasta: int | None = Field(None, ge=0, le=1, description="Has pasta (0/1)")
    has_tofu: int | None = Field(None, ge=0, le=1, description="Has tofu (0/1)")
    has_nuts: int | None = Field(None, ge=0, le=1, description="Has nuts (0/1)")
    has_peanut: int | None = Field(None, ge=0, le=1, description="Has peanut (0/1)")
    is_gluten_free: int | None = Field(None, ge=0, le=1, description="Is gluten free (0/1)")
    has_dairy: int | None = Field(None, ge=0, le=1, description="Has dairy (0/1)")
    is_spicy: int | None = Field(None, ge=0, le=1, description="Is spicy (0/1)")
    is_fried: int | None = Field(None, ge=0, le=1, description="Is fried (0/1)")
    is_raw: int | None = Field(None, ge=0, le=1, description="Is raw (0/1)")
    has_coffee: int | None = Field(None, ge=0, le=1, description="Has coffee (0/1)")
    has_greens: int | None = Field(None, ge=0, le=1, description="Has greens (0/1)")
    has_corn: int | None = Field(None, ge=0, le=1, description="Has corn (0/1)")
    has_alcohol: int | None = Field(None, ge=0, le=1, description="Has alcohol (0/1)")
    is_beer: int | None = Field(None, ge=0, le=1, description="Is beer (0/1)")
    is_wine: int | None = Field(None, ge=0, le=1, description="Is wine (0/1)")
    is_multiple_drinks: int | None = Field(None, ge=0, le=1, description="Multiple drinks (0/1)")
    has_thc: int | None = Field(None, ge=0, le=1, description="Has THC (0/1)")


class EntryCreate(EntryBase):
    """Request schema for creating a health entry."""

    @model_validator(mode="before")
    @classmethod
    def validate_date_required(cls, data: dict) -> dict:
        """Ensure date field is provided."""
        if isinstance(data, dict) and data.get("date") is None:
            raise ValueError("date field is required")
        return data

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2025-10-24",
                "meal": "tacos",
                "alcohol": "beer",
                "stress": 4,
                "sleep_hours": 7.5,
                "pain_level": 2,
                "notes": "felt good",
                "has_corn": 1,
                "has_dairy": 1,
                "has_alcohol": 1,
                "is_beer": 1,
            }
        }
    )


class EntryUpdate(EntryBase):
    """Request schema for updating a health entry."""

    id: str = Field(..., description="Entry ID (16-char hash)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a3f8d9c2b1e4f567",
                "notes": "updated notes",
                "pain_level": 3,
                "has_dairy": 0,
            }
        }
    )


class Entry(EntryCreate):
    """Response schema for a health entry."""

    id: str
    created_at: datetime


class SuccessResponse(BaseModel):
    """Generic success response."""

    status: str = "ok"
    message: str | None = None


class EntryResponse(SuccessResponse):
    """Response after creating an entry."""

    entry_id: str


class EntriesResponse(BaseModel):
    """Response for listing entries."""

    count: int
    entries: list[Entry]


class GetEntriesRequest(BaseModel):
    """Request schema for getting entries with optional date filtering."""

    limit: int = Field(10, ge=1, le=100, description="Maximum number of entries to return")
    offset: int = Field(0, ge=0, description="Number of entries to skip")
    start_date: str | None = Field(
        None, description="Filter entries on or after this date (YYYY-MM-DD)"
    )
    end_date: str | None = Field(
        None, description="Filter entries on or before this date (YYYY-MM-DD)"
    )

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, value: str | None) -> str | None:
        """Validate date format is YYYY-MM-DD."""
        if value is None:
            return value
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format") from None


class MetricStats(BaseModel):
    """Statistics for a single metric."""

    avg: float | None = None
    min: float | int | None = None
    max: float | int | None = None
    median: float | None = None
    std: float | None = None
    count: int = 0


class SummaryMetrics(BaseModel):
    """Metrics collection for summary."""

    stress: MetricStats
    sleep_hours: MetricStats
    pain_level: MetricStats


class SummaryData(BaseModel):
    """Complete summary data structure."""

    count: int
    window_days: int
    metrics: SummaryMetrics


class SummaryResponse(BaseModel):
    """Response for health summary."""

    window_days: int
    summary: SummaryData


class PredictionResponse(BaseModel):
    """Response for prediction."""

    based_on_date: str = Field(
        ..., description="Date used as reference for prediction (YYYY-MM-DD)"
    )
    prediction_for_date: str = Field(
        ..., description="Date being predicted (day after based_on_date)"
    )
    predicted_pain_level: float | None = Field(None, description="Predicted pain level (0-10)")
    confidence: float | None = Field(None, ge=0, le=1, description="Model confidence (0-1)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "based_on_date": "2025-06-22",
                "prediction_for_date": "2025-06-23",
                "predicted_pain_level": 2.5,
                "confidence": 0.94,
            }
        }
    )


class CorrelationResponse(BaseModel):
    """Response for correlation analysis."""

    correlations: dict


class UserProfileRequest(BaseModel):
    """Request schema for creating or updating user profile."""

    dietary_restrictions: list[str] = Field(
        default_factory=list,
        description="Dietary restrictions (e.g., ['gluten-free', 'vegan'])",
    )
    allergies: list[str] = Field(
        default_factory=list,
        description="Food allergies (e.g., ['peanuts', 'shellfish'])",
    )
    preferences: dict[str, str] = Field(
        default_factory=dict,
        description="Food preferences (e.g., {'milk_type': 'oat', 'tortilla_type': 'flour'})",
    )
    habits: dict[str, str] = Field(
        default_factory=dict,
        description="Dietary habits (e.g., {'typical_breakfast': 'cereal with oat milk'})",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dietary_restrictions": ["gluten-free", "lactose-intolerant"],
                "allergies": [],
                "preferences": {"milk_type": "oat", "tortilla_type": "flour"},
                "habits": {"typical_breakfast": "cereal with oat milk"},
            }
        }
    )


class UserProfileResponse(UserProfileRequest):
    """Response schema for user profile."""

    id: str
    created_at: datetime
    updated_at: datetime
    date_last_confirmed: datetime | None = Field(
        None, description="Date when profile was last validated"
    )
    profile_stale: bool = Field(
        False, description="Whether profile is older than 30 days and needs refresh"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "default_user",
                "dietary_restrictions": ["gluten-free", "lactose-intolerant"],
                "allergies": [],
                "preferences": {"milk_type": "oat", "tortilla_type": "flour"},
                "habits": {"typical_breakfast": "cereal with oat milk"},
                "created_at": "2025-11-03T10:30:00",
                "updated_at": "2025-11-03T10:30:00",
                "date_last_confirmed": "2025-11-03T10:30:00",
                "profile_stale": False,
            }
        }
    )
