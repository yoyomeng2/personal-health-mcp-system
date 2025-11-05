"""Unit tests for training script."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from personal_health.exceptions import ModelError
from scripts.train_model import (
    _extract_features_for_entry,
    _generate_feature_importance_plot,
    _generate_prediction_plot,
    _get_feature_names,
    _log_feature_importance,
    train_pain_prediction_model,
)


class TestExtractFeaturesForEntry:
    """Test feature extraction for a single entry."""

    def test_returns_none_for_invalid_date(self):
        """Test that invalid date format returns None."""
        entries = []
        features, has_data = _extract_features_for_entry("invalid-date", entries)

        assert features is None
        assert has_data is False

    def test_returns_none_for_insufficient_prior_entries(self):
        """Test that insufficient prior entries (< 3 days) returns None."""
        entry_date = "2024-01-10"
        entries = [
            {"date": "2024-01-09", "stress": 5, "sleep_hours": 7, "pain_level": 3},
            {"date": "2024-01-08", "stress": 4, "sleep_hours": 8, "pain_level": 2},
            # Only 2 prior entries (need at least 3)
        ]

        features, has_data = _extract_features_for_entry(entry_date, entries)

        assert features is None
        assert has_data is False

    def test_extracts_features_with_minimum_data(self):
        """Test feature extraction with minimum 3 days of data."""
        entry_date = "2024-01-10"
        entries = [
            {
                "date": "2024-01-09",
                "stress": 5,
                "sleep_hours": 7,
                "pain_level": 3,
                "meal": "pasta",
                "alcohol": None,
            },
            {
                "date": "2024-01-08",
                "stress": 4,
                "sleep_hours": 8,
                "pain_level": 2,
                "meal": "salad",
                "alcohol": None,
            },
            {
                "date": "2024-01-07",
                "stress": 6,
                "sleep_hours": 6,
                "pain_level": 4,
                "meal": "pizza",
                "alcohol": "beer",
            },
        ]

        features, has_data = _extract_features_for_entry(entry_date, entries)

        assert has_data is True
        assert features is not None
        assert isinstance(features, list)
        # 7 stress + 7 sleep + 7 pain + 1 day_of_week + 6 rolling stats + meal/alcohol features
        assert len(features) > 21  # At least the core features

    def test_extracts_features_with_full_week_data(self):
        """Test feature extraction with full 7 days of data."""
        entry_date = "2024-01-15"
        entries = []

        # Create 7 days of prior entries
        for i in range(1, 8):
            date = datetime(2024, 1, 15) - timedelta(days=i)
            entries.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "stress": 5 + i,
                    "sleep_hours": 7 + i % 2,
                    "pain_level": 3 + i % 3,
                    "meal": "test meal",
                    "alcohol": None,
                }
            )

        features, has_data = _extract_features_for_entry(entry_date, entries)

        assert has_data is True
        assert features is not None
        # Should have all features extracted
        assert len(features) > 21

    def test_pads_missing_days_with_zeros(self):
        """Test that missing days are padded with zeros."""
        entry_date = "2024-01-10"
        entries = [
            {
                "date": "2024-01-09",
                "stress": 5,
                "sleep_hours": 7,
                "pain_level": 3,
                "meal": "pasta",
                "alcohol": None,
            },
            {
                "date": "2024-01-08",
                "stress": 4,
                "sleep_hours": 8,
                "pain_level": 2,
                "meal": "salad",
                "alcohol": None,
            },
            {
                "date": "2024-01-07",
                "stress": 6,
                "sleep_hours": 6,
                "pain_level": 4,
                "meal": "pizza",
                "alcohol": None,
            },
            # Missing days 4-7
        ]

        features, has_data = _extract_features_for_entry(entry_date, entries)

        assert has_data is True
        assert features is not None
        # First 21 values are the lag features (7 days * 3 metrics)
        # Days 4-7 should be padded with 0.0
        stress_7d = features[0:7]
        sleep_7d = features[7:14]
        pain_7d = features[14:21]

        # Last 4 days should be zeros (indices 3-6)
        assert stress_7d[3:7] == [0.0, 0.0, 0.0, 0.0]
        assert sleep_7d[3:7] == [0.0, 0.0, 0.0, 0.0]
        assert pain_7d[3:7] == [0.0, 0.0, 0.0, 0.0]

    def test_handles_none_values_in_entries(self):
        """Test that None values are handled gracefully."""
        entry_date = "2024-01-10"
        entries: list[dict[Any, Any]] = [
            {
                "date": "2024-01-09",
                "stress": None,
                "sleep_hours": 7,
                "pain_level": 3,
                "meal": None,
                "alcohol": None,
            },
            {
                "date": "2024-01-08",
                "stress": 4,
                "sleep_hours": None,
                "pain_level": 2,
                "meal": "salad",
                "alcohol": None,
            },
            {
                "date": "2024-01-07",
                "stress": 6,
                "sleep_hours": 6,
                "pain_level": None,
                "meal": "pizza",
                "alcohol": None,
            },
        ]

        features, has_data = _extract_features_for_entry(entry_date, entries)

        assert has_data is True
        assert features is not None
        # None values should be converted to 0.0
        assert all(isinstance(f, float) for f in features)

    def test_includes_day_of_week_feature(self):
        """Test that day of week is included as a feature."""
        # 2024-01-15 is a Monday (weekday = 0)
        entry_date = "2024-01-15"
        entries = [
            {
                "date": "2024-01-14",
                "stress": 5,
                "sleep_hours": 7,
                "pain_level": 3,
                "meal": "pasta",
                "alcohol": None,
            },
            {
                "date": "2024-01-13",
                "stress": 4,
                "sleep_hours": 8,
                "pain_level": 2,
                "meal": "salad",
                "alcohol": None,
            },
            {
                "date": "2024-01-12",
                "stress": 6,
                "sleep_hours": 6,
                "pain_level": 4,
                "meal": "pizza",
                "alcohol": None,
            },
        ]

        features, has_data = _extract_features_for_entry(entry_date, entries)

        assert has_data is True
        assert features is not None
        # Day of week should be at index 21 (after 7+7+7 lag features)
        day_of_week = features[21]
        assert day_of_week == 0.0  # Monday


class TestGetFeatureNames:
    """Test feature name generation."""

    def test_returns_list_of_strings(self):
        """Test that feature names are returned as list of strings."""
        feature_names = _get_feature_names()

        assert isinstance(feature_names, list)
        assert all(isinstance(name, str) for name in feature_names)

    def test_includes_lag_features(self):
        """Test that lag features are included."""
        feature_names = _get_feature_names()

        # Should include stress_day_1 through stress_day_7
        assert "stress_day_1" in feature_names
        assert "stress_day_7" in feature_names
        assert "sleep_day_1" in feature_names
        assert "pain_day_1" in feature_names

    def test_includes_temporal_features(self):
        """Test that temporal features are included."""
        feature_names = _get_feature_names()

        # Should include day of week
        assert "day_of_week" in feature_names

    def test_includes_rolling_stats(self):
        """Test that rolling statistics are included."""
        feature_names = _get_feature_names()

        # Should include rolling stats like average_stress, max_stress, etc.
        assert "average_stress" in feature_names
        assert "max_stress" in feature_names
        assert "average_pain" in feature_names


class TestLogFeatureImportance:
    """Test feature importance logging."""

    def test_logs_top_features(self, caplog):
        """Test that top features are logged."""
        feature_names = ["feature_a", "feature_b", "feature_c"]
        importances = np.array([0.5, 0.3, 0.2])

        with caplog.at_level("INFO"):
            _log_feature_importance(feature_names, importances)

        # Should log the features in order of importance
        assert "feature_a" in caplog.text
        assert "0.5000" in caplog.text

    def test_limits_to_top_20(self, caplog):
        """Test that only top 20 features are logged."""
        feature_names = [f"feature_{i}" for i in range(30)]
        importances = np.random.rand(30)

        with caplog.at_level("INFO"):
            _log_feature_importance(feature_names, importances)

        # Should mention "Top 20"
        assert "Top 20" in caplog.text


class TestGeneratePredictionPlot:
    """Test prediction plot generation."""

    @patch("scripts.train_model.plt")
    def test_creates_plot_file(self, mock_plt):
        """Test that plot file is created."""
        output_path = Path("data/model_v1.pkl")
        y_test = [1, 2, 3, 4, 5]
        y_pred = np.array([1.1, 2.2, 2.9, 4.1, 5.2])

        _generate_prediction_plot(output_path, y_test, y_pred, 0.2, 0.3, 0.95, 0.15)

        # Should call savefig
        mock_plt.savefig.assert_called_once()
        call_args = mock_plt.savefig.call_args[0][0]
        assert "predicted_vs_actual.png" in str(call_args)


class TestGenerateFeatureImportancePlot:
    """Test feature importance plot generation."""

    @patch("scripts.train_model.plt")
    def test_creates_plot_file(self, mock_plt):
        """Test that plot file is created."""
        output_path = Path("data/model_v1.pkl")
        feature_names = ["feature_a", "feature_b", "feature_c"]
        importances = np.array([0.5, 0.3, 0.2])

        _generate_feature_importance_plot(output_path, feature_names, importances)

        # Should call savefig
        mock_plt.savefig.assert_called_once()
        call_args = mock_plt.savefig.call_args[0][0]
        assert "feature_importance.png" in str(call_args)


class TestTrainPainPredictionModel:
    """Test main training function."""

    @patch("scripts.train_model.Database")
    @patch("scripts.train_model.joblib.dump")
    def test_raises_error_for_no_entries(self, mock_dump, mock_db_class):
        """Test that ModelError is raised when no entries exist."""
        # Mock database with no entries
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_db.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.connect.return_value.__exit__ = Mock(return_value=None)

        with pytest.raises(ModelError, match="Training failed"):
            train_pain_prediction_model(db_path="test.db", output_path="test.pkl")

    @patch("scripts.train_model.Database")
    @patch("scripts.train_model.joblib.dump")
    def test_raises_error_for_insufficient_training_data(self, mock_dump, mock_db_class):
        """Test that ModelError is raised when insufficient training samples."""
        # Mock database with only a few entries (< 10 training samples)
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Create minimal entries (not enough for training)
        rows = [
            {
                "date": "2024-01-01",
                "stress": 5,
                "sleep_hours": 7,
                "pain_level": 3,
                "meal": None,
                "alcohol": None,
            },
            {
                "date": "2024-01-02",
                "stress": 4,
                "sleep_hours": 8,
                "pain_level": 2,
                "meal": None,
                "alcohol": None,
            },
        ]
        mock_cursor.fetchall.return_value = rows
        mock_conn.cursor.return_value = mock_cursor
        mock_db.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.connect.return_value.__exit__ = Mock(return_value=None)

        with pytest.raises(ModelError, match="Training failed"):
            train_pain_prediction_model(db_path="test.db", output_path="test.pkl")

    @patch("scripts.train_model.Database")
    @patch("scripts.train_model.joblib.dump")
    @patch("scripts.train_model._generate_prediction_plot")
    @patch("scripts.train_model._generate_feature_importance_plot")
    def test_trains_model_successfully(
        self,
        mock_importance_plot,
        mock_pred_plot,
        mock_dump,
        mock_db_class,
    ):
        """Test successful model training with sufficient data."""
        # Mock database with sufficient entries
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Create entries spanning multiple days for training
        rows = []
        base_date = datetime(2024, 1, 1)
        for i in range(30):  # 30 days of data
            date = base_date + timedelta(days=i)
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "stress": 5 + (i % 3),
                    "sleep_hours": 7 + (i % 2),
                    "pain_level": 3 + (i % 4),
                    "meal": "test meal",
                    "alcohol": None if i % 2 == 0 else "beer",
                }
            )

        mock_cursor.fetchall.return_value = rows
        mock_conn.cursor.return_value = mock_cursor
        mock_db.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.connect.return_value.__exit__ = Mock(return_value=None)

        # Should not raise an error
        train_pain_prediction_model(db_path="test.db", output_path="test.pkl")

        # Should save the model
        mock_dump.assert_called_once()

    @patch("scripts.train_model.Database")
    @patch("scripts.train_model.joblib.dump")
    def test_creates_output_directory(self, mock_dump, mock_db_class, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        # Mock database with sufficient entries
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Create entries spanning multiple days
        rows = []
        base_date = datetime(2024, 1, 1)
        for i in range(30):
            date = base_date + timedelta(days=i)
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "stress": 5,
                    "sleep_hours": 7,
                    "pain_level": 3,
                    "meal": "test",
                    "alcohol": None,
                }
            )

        mock_cursor.fetchall.return_value = rows
        mock_conn.cursor.return_value = mock_cursor
        mock_db.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.connect.return_value.__exit__ = Mock(return_value=None)

        output_path = tmp_path / "models" / "test_model.pkl"
        assert not output_path.parent.exists()

        train_pain_prediction_model(db_path="test.db", output_path=output_path)

        # Directory should be created
        assert output_path.parent.exists()
