"""Base LLM provider interface."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from personal_health.db.schemas import EntrySchema


@dataclass
class UserProfile:
    """User dietary profile for context-aware extraction.

    This is the working model for LLM providers with Python types.
    Use from_db() to convert from database UserProfileSchema.
    """

    dietary_restrictions: list[str]
    allergies: list[str]
    preferences: dict[str, Any]
    habits: dict[str, Any]

    @classmethod
    def from_db(cls, db_profile: dict[str, Any]) -> UserProfile:
        """Convert database profile (JSON strings) to UserProfile (Python types).

        Args:
            db_profile (dict): Database profile with JSON string fields.

        Returns:
            UserProfile: UserProfile instance with parsed Python types.
        """
        return cls(
            dietary_restrictions=json.loads(db_profile.get("dietary_restrictions", "[]")),
            allergies=json.loads(db_profile.get("allergies", "[]")),
            preferences=json.loads(db_profile.get("preferences", "{}")),
            habits=json.loads(db_profile.get("habits", "{}")),
        )


@dataclass
class ExtractedFeatures:
    """Result of feature extraction from meal description.

    Attributes:
        features (dict[str, int | None]): Extracted binary features (0, 1, or None).
        confidence (dict[str, str]): Confidence level for each feature ("explicit", "inferred", "unknown").
        reasoning (dict[str, str]): Explanation for each feature decision.
    """

    features: dict[str, int | None]
    confidence: dict[str, str]
    reasoning: dict[str, str]


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def extract_features(self, entry: EntrySchema, user_profile: UserProfile) -> ExtractedFeatures:
        """Extract binary features from entry using user profile context.

        Args:
            entry (EntrySchema): Database entry with meal, alcohol, and notes fields.
            user_profile (UserProfile): User's dietary profile for context.

        Returns:
            ExtractedFeatures: Extracted features with confidence and reasoning.
        """
        pass
