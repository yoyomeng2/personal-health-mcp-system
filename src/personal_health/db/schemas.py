"""Database models (Pydantic schemas for tables)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EntrySchema(BaseModel):
    """Database model for entries table."""

    id: str = Field(..., description="Entry ID (16-char hash)")
    date: str = Field(..., description="Entry date in YYYY-MM-DD format")
    meal: str | None = Field(None, description="Meal description")
    alcohol: str | None = Field(None, description="Alcohol consumption")
    stress: int | None = Field(None, ge=0, le=10, description="Stress level (0-10)")
    sleep_hours: float | None = Field(None, ge=0, le=24, description="Sleep hours")
    pain_level: int | None = Field(None, ge=0, le=10, description="Pain level (0-10)")
    notes: str | None = Field(None, description="Additional notes")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    # Feature columns
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


class UserProfileSchema(BaseModel):
    """Database model for user_profile table."""

    id: str = Field(default="default_user", description="User ID")
    dietary_restrictions: str = Field(
        default="[]", description="JSON array of dietary restrictions"
    )
    allergies: str = Field(default="[]", description="JSON array of allergies")
    preferences: str = Field(default="{}", description="JSON object of preferences")
    habits: str = Field(default="{}", description="JSON object of habits")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Update timestamp")
    date_last_confirmed: datetime | None = Field(None, description="Last confirmation timestamp")


class MigrationSchema(BaseModel):
    """Database model for _migrations table."""

    id: int = Field(..., description="Migration ID")
    migration_name: str = Field(..., description="Migration filename")
    executed_at: datetime = Field(default_factory=datetime.now, description="Execution timestamp")
