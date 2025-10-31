"""Model predictor for health predictions."""

from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np

from personal_health.config import Config
from personal_health.db import Database
from personal_health.exceptions import ModelError
from personal_health.logging_config import get_logger
from personal_health.ml import extract_meal_alcohol_features
from personal_health.ml.features import LagFeature

logger = get_logger(__name__)


class HealthPredictor:
    """Predictor for health outcomes."""

    def __init__(self, model_path: Path | str = "data/model_v1.pkl") -> None:
        """Initialize predictor.

        Args:
            model_path: Path to trained model artifact.
        """
        self._config = Config()
        self.model_path = (
            Path(self._config.get("model.predictor_path", model_path))
            if isinstance(model_path, str)
            else model_path
        )
        self.model = None

    def load(self) -> None:
        """Load model from disk.

        Raises:
            ModelError: If model cannot be loaded.
        """
        if not self.model_path.exists():
            logger.warning(f"Model file not found: {self.model_path}")
            return

        self.model = joblib.load(str(self.model_path))
        logger.info(f"Model loaded: {self.model_path}")

    def predict(self, prediction_date: str, db: Database) -> dict:
        """Predict pain level for a given date.

        Args:
            prediction_date: Target prediction date in YYYY-MM-DD format.
            db: Database instance to query historical entries.

        Returns:
            Dictionary with keys: prediction (float), confidence (float), status (str).
            Returns None values if model not loaded or prediction fails.
        """
        if self.model is None:
            logger.warning("Model not loaded")
            return {
                "prediction": None,
                "confidence": None,
                "status": "Model not loaded",
            }

        if np is None:
            raise ModelError("numpy not installed")

        try:
            # Extract features
            features, status = self._extract_features(prediction_date, db)

            if features is None:
                logger.warning(f"Feature extraction failed: {status}")
                return {"prediction": None, "confidence": None, "status": status}

            # Make prediction
            feature_array = np.array([features])
            prediction = float(self.model.predict(feature_array)[0])

            # Clamp prediction to valid pain range (0-10)
            prediction = max(0.0, min(10.0, prediction))

            # Estimate confidence from model's prediction std (using trees)
            if hasattr(self.model, "estimators_"):
                # RandomForest: get std of individual tree predictions
                tree_predictions = np.array(
                    [tree.predict(feature_array)[0] for tree in self.model.estimators_]
                )
                confidence = float(1.0 - (np.std(tree_predictions) / 10.0))
                confidence = max(0.0, min(1.0, confidence))
            else:
                confidence = 0.5

            logger.info(
                f"Prediction for {prediction_date}: {prediction:.1f} (confidence: {confidence:.2f})"
            )

            return {
                "prediction": prediction,
                "confidence": confidence,
                "status": "ok",
            }
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {"prediction": None, "confidence": None, "status": f"Prediction error: {e}"}

    def _extract_features(
        self, prediction_date: str, db: Database
    ) -> tuple[list[float] | None, str]:
        """Extract features for a given prediction date from database.

        Args:
            prediction_date: Target prediction date in YYYY-MM-DD format.
            db: Database instance to query historical entries.

        Returns:
            Tuple of (feature_array, status_message) where feature_array is
            a list of 25 features or None if insufficient data.
        """
        try:
            pred_dt = datetime.strptime(prediction_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None, f"Invalid date format: {prediction_date}"

        # Load all entries from database
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entries ORDER BY date ASC")
            rows = cursor.fetchall()

        if not rows:
            return None, "No historical data available"

        # Convert rows to dictionaries
        entries = [dict(row) for row in rows]

        # Get entries from prior 7 days (days -7 to -1 before the prediction date)
        prior_entries = []
        for i in range(1, 8):  # 1 to 7 days before
            target_day = pred_dt - timedelta(days=i)
            for entry in entries:
                try:
                    entry_date_parsed = datetime.strptime(entry["date"], "%Y-%m-%d").date()
                    if entry_date_parsed == target_day:
                        prior_entries.append(entry)
                        break
                except (ValueError, KeyError):
                    continue

        # Check if we have enough data (ideally 7 days, but allow minimum of 3)
        if len(prior_entries) < 3:
            return (
                None,
                f"Insufficient prior entries: found {len(prior_entries)}/7, need at least 3",
            )

        # Sort by date descending (most recent first)
        prior_entries.sort(key=lambda e: e["date"], reverse=True)

        # Extract individual day values (pad with 0 if missing)
        stress_7d = []
        sleep_7d = []
        pain_7d = []

        for i in range(7):
            if i < len(prior_entries):
                entry = prior_entries[i]
                stress_7d.append(float(entry.get(LagFeature.STRESS.value) or 0))
                sleep_7d.append(float(entry.get(LagFeature.SLEEP_HOURS.value) or 0))
                pain_7d.append(float(entry.get(LagFeature.PAIN_LEVEL.value) or 0))
            else:
                stress_7d.append(0.0)
                sleep_7d.append(0.0)
                pain_7d.append(0.0)

        # Compute rolling statistics
        stress_values = [
            float(e[LagFeature.STRESS.value])
            for e in prior_entries
            if e.get(LagFeature.STRESS.value) is not None
        ]
        sleep_values = [
            float(e[LagFeature.SLEEP_HOURS.value])
            for e in prior_entries
            if e.get(LagFeature.SLEEP_HOURS.value) is not None
        ]
        pain_values = [
            float(e[LagFeature.PAIN_LEVEL.value])
            for e in prior_entries
            if e.get(LagFeature.PAIN_LEVEL.value) is not None
        ]

        if np is None:
            raise ModelError("numpy not installed")

        avg_stress = float(np.mean(stress_values)) if stress_values else 0.0
        max_stress = float(np.max(stress_values)) if stress_values else 0.0
        avg_sleep = float(np.mean(sleep_values)) if sleep_values else 0.0
        min_sleep = float(np.min(sleep_values)) if sleep_values else 0.0
        avg_pain = float(np.mean(pain_values)) if pain_values else 0.0
        max_pain = float(np.max(pain_values)) if pain_values else 0.0

        # Day of week (0 = Monday, 6 = Sunday)
        day_of_week = float(pred_dt.weekday())

        # Extract meal and alcohol features from most recent entry
        most_recent_entry = prior_entries[0] if prior_entries else {}
        meal_alcohol_features = extract_meal_alcohol_features(
            most_recent_entry.get("meal"), most_recent_entry.get("alcohol")
        )

        # Combine features: 7 stress + 7 sleep + 7 pain + day_of_week + rolling stats + meal/alcohol
        features = (
            stress_7d
            + sleep_7d
            + pain_7d
            + [day_of_week, avg_stress, max_stress, avg_sleep, min_sleep, avg_pain, max_pain]
            + meal_alcohol_features
        )

        return features, "ok"
