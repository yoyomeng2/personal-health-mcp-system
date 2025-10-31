"""Machine Learning module for Personal Health MCP System."""

from __future__ import annotations

from personal_health.ml.features import extract_meal_alcohol_features
from personal_health.ml.predictor import HealthPredictor

__all__ = [
    "HealthPredictor",
    "extract_meal_alcohol_features",
]
