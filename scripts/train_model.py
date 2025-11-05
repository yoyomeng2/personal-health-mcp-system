"""Training script for health prediction model."""

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
from matplotlib import pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    max_error,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)

from personal_health.config import Config
from personal_health.db import Database
from personal_health.exceptions import ModelError
from personal_health.logging_config import get_logger, setup_logging
from personal_health.ml.features import (
    AlcoholFeature,
    LagFeature,
    MealFeature,
    RollingStatFeature,
    SubstanceFeature,
    TemporalFeature,
)

logger = get_logger(__name__)


def train_pain_prediction_model(
    db_path: Path | str = "data/health.db",
    output_path: Path | str = "data/model_v1.pkl",
) -> None:
    """Train pain prediction model using historical entries with a Random Forest regressor.

    Args:
        db_path: Path to SQLite database.
        output_path: Path to save trained model.

    Raises:
        ModelError: If training fails or insufficient data available.

    Note:
        Model predicts pain_level (0-10) for the next day based on prior 7 days
        of stress, sleep, and pain data. Requires at least 10 training samples.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        logger.info("Starting pain prediction model training...")

        # Load all entries from database
        db = Database(db_path)
        db.init()

        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entries ORDER BY date ASC")
            rows = cursor.fetchall()

        if not rows:
            raise ModelError("No entries found in database for training")

        # Convert rows to dictionaries
        entries = [dict(row) for row in rows]
        logger.info(f"Loaded {len(entries)} entries from database")

        # Extract features and targets
        x = []
        y = []

        for i, entry in enumerate(entries):
            # Get the next day's pain level as target
            if i + 1 >= len(entries):
                continue  # Skip last entry (no next day target)

            entry_date = entry["date"]
            target_entry = entries[i + 1]

            # Extract features from prior 7 days
            features, has_data = _extract_features_for_entry(entry_date, entries)

            if features and has_data and target_entry.get(LagFeature.PAIN_LEVEL.value) is not None:
                x.append(features)
                y.append(float(target_entry[LagFeature.PAIN_LEVEL.value]))

        if len(x) < 10:
            raise ModelError(f"Insufficient training data: {len(x)} samples, need at least 10")

        logger.info(f"Prepared {len(x)} training samples with {len(x[0])} features")

        # Split data: chronologically (80% train, 20% test)
        split_idx = int(len(x) * 0.8)
        x_train = x[:split_idx]
        y_train = y[:split_idx]
        x_test = x[split_idx:]
        y_test = y[split_idx:]

        logger.info(f"Training on {len(x_train)} samples, testing on {len(x_test)} samples")

        # Train Random Forest model
        model = RandomForestRegressor(
            n_estimators=50,
            max_depth=10,
            min_samples_split=3,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(x_train, y_train)

        # Evaluate on test set
        y_pred = model.predict(x_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        mape = mean_absolute_percentage_error(y_test, y_pred)
        medae = median_absolute_error(y_test, y_pred)
        max_err = max_error(y_test, y_pred)

        logger.info(
            f"""Model evaluation -

                    MAE: {mae:.2f},
                    RMSE: {rmse:.2f},
                    R-squared: {r2:.2f},
                    MAPE: {mape:.2f},
                    MedAE: {medae:.2f},
                    Max Error: {max_err:.2f}"""
        )

        # predicted v actual plot
        _generate_prediction_plot(output_path, y_test, y_pred, mae, rmse, r2, float(medae))

        # feature importance analysis
        feature_names = _get_feature_names()
        _log_feature_importance(feature_names, model.feature_importances_)
        _generate_feature_importance_plot(output_path, feature_names, model.feature_importances_)

        # Save model
        joblib.dump(model, str(output_path))
        logger.info(f"Model trained and saved to {output_path}")

    except Exception as e:
        raise ModelError("Training failed") from e


def _generate_prediction_plot(
    output_path: Path,
    y_test: list,
    y_pred: np.ndarray,
    mae: float,
    rmse: float,
    r2: float,
    medae: float,
) -> None:
    """Generate a scatter plot comparing predicted vs actual pain levels, with a reference line for perfect predictions and a text box showing evaluation metrics.

    Args:
        output_path (str): Path to save the generated plot.
        y_test (list): List of actual pain levels from the test set.
        y_pred (np.ndarray): Array of predicted pain levels from the model for the test set.
        mae (float): Mean Absolute Error of the predictions.
        rmse (float): Root Mean Squared Error of the predictions.
        r2 (float): R-squared score of the predictions.
        medae (float): Median Absolute Error of the predictions.
    """
    plt.figure(figsize=(8, 8))
    plt.scatter(y_test, y_pred, alpha=0.6, edgecolors="k", s=50)

    # Perfect prediction line
    min_val = min(min(y_test), min(y_pred))
    max_val = max(max(y_test), max(y_pred))
    plt.plot([min_val, max_val], [min_val, max_val], "r--", lw=2, label="Perfect prediction")

    plt.xlabel("Actual Pain Level", fontsize=12)
    plt.ylabel("Predicted Pain Level", fontsize=12)
    plt.title("Predicted vs Actual Pain Levels", fontsize=14, fontweight="bold")
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)

    # Add metrics text box
    textstr = f"MAE: {mae:.2f}\nRMSE: {rmse:.2f}\nR²: {r2:.2f}\nMedAE: {medae:.2f}"
    props = {"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5}
    plt.text(
        0.05,
        0.95,
        textstr,
        transform=plt.gca().transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=props,
    )

    plot_path = output_path.parent / "predicted_vs_actual.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Prediction plot saved to {plot_path}")


def _get_feature_names() -> list[str]:
    """Generate feature names matching the feature extraction order.

    Returns:
        list[str]: List of feature names in the same order as feature extraction.
    """
    # 7-day lag features
    lag_features = []
    for i in range(1, 8):
        lag_features.extend([f"stress_day_{i}", f"sleep_day_{i}", f"pain_day_{i}"])

    # Temporal feature
    temporal_feature_names = [el.value.name for el in TemporalFeature]

    # Rolling statistics
    rolling_feature_names = [el.value.name for el in RollingStatFeature]

    # Binary features from DB (in consistent order)
    binary_feature_names = (
        [el.value.name for el in AlcoholFeature]
        + [el.value.name for el in SubstanceFeature]
        + [el.value.name for el in MealFeature]
    )

    return lag_features + temporal_feature_names + rolling_feature_names + binary_feature_names


def _log_feature_importance(feature_names: list[str], importances: np.ndarray) -> None:
    """Log the top 20 most important features.

    Args:
        feature_names (list[str]): List of feature names.
        importances (np.ndarray): Array of feature importance values.
    """
    # Sort features by importance
    indices = np.argsort(importances)[::-1]

    logger.info("Top 20 Feature Importances:")
    for i in range(min(20, len(feature_names))):
        idx = indices[i]
        logger.info(f"  {i + 1}. {feature_names[idx]}: {importances[idx]:.4f}")


def _generate_feature_importance_plot(
    output_path: Path, feature_names: list[str], importances: np.ndarray
) -> None:
    """Generate a horizontal bar plot of the top 20 feature importances.

    Args:
        output_path (Path): Base path for saving the plot.
        feature_names (list[str]): List of feature names.
        importances (np.ndarray): Array of feature importance values.
    """
    # Sort features by importance
    indices = np.argsort(importances)[::-1]
    top_n = 20
    top_indices = indices[:top_n]
    top_names = [feature_names[i] for i in top_indices]
    top_importances = importances[top_indices]

    # Create horizontal bar plot
    plt.figure(figsize=(10, 8))
    y_pos = np.arange(len(top_names))
    plt.barh(y_pos, top_importances, align="center", alpha=0.8, edgecolor="k")
    plt.yticks(y_pos, top_names, fontsize=9)
    plt.xlabel("Feature Importance", fontsize=12)
    plt.title("Top 20 Feature Importances (Random Forest)", fontsize=14, fontweight="bold")
    plt.gca().invert_yaxis()  # Highest importance at top
    plt.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()

    plot_path = output_path.parent / "feature_importance.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Feature importance plot saved to {plot_path}")


def _extract_features_for_entry(
    entry_date: str, entries: list[dict]
) -> tuple[list[float] | None, bool]:
    """Extract features for a given entry date from historical entries."""
    try:
        entry_dt = datetime.strptime(entry_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None, False

    # Get entries from prior 7 days (days -7 to -1 before the target date)
    prior_entries = []
    for i in range(1, 8):  # 1 to 7 days before
        target_day = entry_dt - timedelta(days=i)
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
        logger.debug(f"Insufficient prior entries for {entry_date}: found {len(prior_entries)}/7")
        return None, False

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

    # rolling stats
    avg_stress = float(np.mean(stress_values)) if stress_values else 0.0
    max_stress = float(np.max(stress_values)) if stress_values else 0.0
    avg_sleep = float(np.mean(sleep_values)) if sleep_values else 0.0
    min_sleep = float(np.min(sleep_values)) if sleep_values else 0.0
    avg_pain = float(np.mean(pain_values)) if pain_values else 0.0
    max_pain = float(np.max(pain_values)) if pain_values else 0.0

    # Day of week (0 = Monday, 6 = Sunday)
    day_of_week = float(entry_dt.weekday())

    # Extract binary features from most recent entry's DB columns
    most_recent_entry = prior_entries[0] if prior_entries else {}

    # Binary features (using enums to maintain consistent order with _get_feature_names)
    binary_features = (
        [float(most_recent_entry.get(el.value.name) or 0) for el in AlcoholFeature]
        + [float(most_recent_entry.get(el.value.name) or 0) for el in SubstanceFeature]
        + [float(most_recent_entry.get(el.value.name) or 0) for el in MealFeature]
    )

    # Combine features: 7 stress + 7 sleep + 7 pain + day_of_week + rolling stats + binary features
    features = (
        stress_7d
        + sleep_7d
        + pain_7d
        + [
            day_of_week,
            avg_stress,
            max_stress,
            avg_sleep,
            min_sleep,
            avg_pain,
            max_pain,
        ]
        + binary_features
    )

    return features, True


def main() -> None:
    """CLI entry point for training the model."""
    parser = argparse.ArgumentParser(
        description="Train pain prediction model from health database entries"
    )
    parser.add_argument(
        "--db",
        default="data/health.db",
        help="Path to SQLite database file (default: data/health.db)",
    )
    parser.add_argument(
        "--model",
        default="data/model_v1.pkl",
        help="Path to save trained model file (default: data/model_v1.pkl)",
    )
    args = parser.parse_args()

    config = Config()
    log_level = config.get("logging.level", "INFO")
    setup_logging(level=log_level)

    train_pain_prediction_model(db_path=args.db, output_path=args.model)


if __name__ == "__main__":
    main()
