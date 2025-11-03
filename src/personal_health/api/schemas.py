"""MCP API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EntryCreate(BaseModel):
    """Request schema for creating a health entry."""

    date: str = Field(..., description="Entry date in YYYY-MM-DD format")
    meal: str | None = Field(None, description="Meal description")
    alcohol: str | None = Field(None, description="Alcohol consumption")
    stress: int | None = Field(None, ge=0, le=10, description="Stress level (0-10)")
    sleep_hours: float | None = Field(None, ge=0, le=24, description="Sleep hours")
    pain_level: int | None = Field(None, ge=0, le=10, description="Pain level (0-10)")
    notes: str | None = Field(None, description="Additional notes")

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
            }
        }
    )


class EntryUpdate(BaseModel):
    """Request schema for updating a health entry."""

    id: str = Field(..., description="Entry ID (16-char hash)")
    date: str | None = Field(None, description="Entry date in YYYY-MM-DD format")
    meal: str | None = Field(None, description="Meal description")
    alcohol: str | None = Field(None, description="Alcohol consumption")
    stress: int | None = Field(None, ge=0, le=10, description="Stress level (0-10)")
    sleep_hours: float | None = Field(None, ge=0, le=24, description="Sleep hours")
    pain_level: int | None = Field(None, ge=0, le=10, description="Pain level (0-10)")
    notes: str | None = Field(None, description="Additional notes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a3f8d9c2b1e4f567",
                "notes": "updated notes",
                "pain_level": 3,
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
