"""Integration tests for API routes."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from personal_health.ml.providers.base import ExtractedFeatures


class TestResetDatabase:
    """Integration tests for /reset_database endpoint."""

    def test_reset_database_success(self, client: TestClient) -> None:
        """Test resetting the database."""
        response = client.post("/reset_database")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data


class TestUserProfile:
    """Integration tests for /user/profile endpoint."""

    def test_get_user_profile_default_user(self, client: TestClient) -> None:
        """Test getting default user profile creates it if not exists."""
        response = client.get("/user/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "default_user"
        assert data["dietary_restrictions"] == []
        assert data["allergies"] == []
        assert data["preferences"] == {}
        assert data["habits"] == {}
        assert "created_at" in data
        assert "updated_at" in data
        assert "profile_stale" in data

    def test_update_user_profile_success(self, client: TestClient) -> None:
        """Test updating user profile with valid data."""
        profile_data = {
            "dietary_restrictions": ["gluten-free", "vegan"],
            "allergies": ["peanuts"],
            "preferences": {"milk_type": "oat"},
            "habits": {"typical_breakfast": "oatmeal"},
        }
        response = client.put("/user/profile?user_id=test_user", json=profile_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_user"
        assert data["dietary_restrictions"] == ["gluten-free", "vegan"]
        assert data["allergies"] == ["peanuts"]
        assert data["preferences"] == {"milk_type": "oat"}
        assert data["habits"] == {"typical_breakfast": "oatmeal"}


class TestAddEntry:
    """Integration tests for /add_entry endpoint."""

    @patch("personal_health.api.routes.generate_entry_id", return_value="test-hash-123")
    def test_add_entry_success(
        self, mock_generate_id: MagicMock, client: TestClient, sample_entry: dict
    ) -> None:
        """Test adding a valid health entry."""
        response = client.post("/add_entry", json=sample_entry)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "entry_id" in data
        assert data["entry_id"] == "test-hash-123"
        mock_generate_id.assert_called_once()

    @patch("personal_health.api.routes.generate_entry_id")
    def test_add_entry_multiple(
        self, mock_generate_id: MagicMock, client: TestClient, sample_entry: dict
    ) -> None:
        """Test adding multiple entries generates unique IDs."""
        mock_generate_id.side_effect = ["hash-1", "hash-2"]

        entry1 = client.post("/add_entry", json=sample_entry).json()
        entry2_data = sample_entry.copy()
        entry2_data["notes"] = "second entry"
        entry2 = client.post("/add_entry", json=entry2_data).json()
        assert entry1["entry_id"] != entry2["entry_id"]
        assert entry1["entry_id"] == "hash-1"
        assert entry2["entry_id"] == "hash-2"

    @patch("personal_health.api.routes.generate_entry_id", return_value="test-hash-456")
    def test_add_entry_with_nullable_fields(
        self, mock_generate_id: MagicMock, client: TestClient
    ) -> None:
        """Test adding entry with minimal required fields."""
        minimal_entry = {
            "date": "2025-10-24",
            "meal": "pizza",
            "alcohol": "beer",
            "stress": 5,
            "sleep_hours": 8,
            "pain_level": 1,
            "notes": "minimal",
        }
        response = client.post("/add_entry", json=minimal_entry)
        assert response.status_code == 200

    def test_add_entry_missing_required_field(self, client: TestClient) -> None:
        """Test that missing required fields are rejected."""
        incomplete_entry = {
            "meal": "pizza",
            "alcohol": "beer",
            "stress": 5,
        }
        response = client.post("/add_entry", json=incomplete_entry)
        assert response.status_code == 422

    def test_duplicate_entry_handling(self, client: TestClient) -> None:
        """Test that duplicate entries are deduplicated via composite key hash."""
        entry_data = {
            "date": "2025-10-28",
            "meal": "duplicate test",
            "alcohol": None,
            "stress": 3,
            "sleep_hours": 8,
            "pain_level": 1,
            "notes": "idempotency test",
        }

        response1 = client.post("/add_entry", json=entry_data)
        assert response1.status_code == 200
        response2 = client.post("/add_entry", json=entry_data)
        assert response2.status_code == 200

        id1 = response1.json()["entry_id"]
        id2 = response2.json()["entry_id"]
        assert id1 == id2, "Should return same ID (deduplication via hash)"

        entries_response = client.get("/get_entries")
        assert entries_response.status_code == 200

        entries = entries_response.json()["entries"]
        test_entries = [e for e in entries if e["meal"] == "duplicate test"]
        assert len(test_entries) == 1, "Only one entry should exist (deduplication worked)"
        assert test_entries[0]["id"] == id1, "Stored entry ID should match the first ID"


class TestUpdateEntry:
    """Integration tests for /update_entry endpoint."""

    @patch("personal_health.api.routes.generate_entry_id", return_value="test-hash-update")
    def test_update_entry_success(
        self, mock_generate_id: MagicMock, client: TestClient, sample_entry: dict
    ) -> None:
        """Test updating an existing entry."""
        create_response = client.post("/add_entry", json=sample_entry)
        assert create_response.status_code == 200
        entry_id = create_response.json()["entry_id"]

        update_data = {"id": entry_id, "notes": "updated notes", "pain_level": 5}
        response = client.put("/update_entry", json=update_data)
        assert response.status_code == 200
        assert response.json()["entry_id"] == entry_id

        entries = client.get("/get_entries").json()["entries"]
        updated_entry = next(e for e in entries if e["id"] == entry_id)
        assert updated_entry["notes"] == "updated notes"
        assert updated_entry["pain_level"] == 5
        assert updated_entry["meal"] == sample_entry["meal"]

    def test_update_entry_not_found(self, client: TestClient) -> None:
        """Test updating non-existent entry returns 404."""
        update_data = {"id": "nonexistent-id", "notes": "test"}
        response = client.put("/update_entry", json=update_data)
        assert response.status_code == 404

    @patch("personal_health.api.routes.generate_entry_id", return_value="test-hash-partial")
    def test_update_entry_partial(
        self, mock_generate_id: MagicMock, client: TestClient, sample_entry: dict
    ) -> None:
        """Test partial update (only some fields)."""
        create_response = client.post("/add_entry", json=sample_entry)
        entry_id = create_response.json()["entry_id"]

        update_data = {"id": entry_id, "notes": "new notes only"}
        response = client.put("/update_entry", json=update_data)
        assert response.status_code == 200

        entries = client.get("/get_entries").json()["entries"]
        updated_entry = next(e for e in entries if e["id"] == entry_id)
        assert updated_entry["notes"] == "new notes only"
        assert updated_entry["stress"] == sample_entry["stress"]

    @patch("personal_health.api.routes.generate_entry_id", return_value="test-hash-noop")
    def test_update_entry_no_fields(
        self, mock_generate_id: MagicMock, client: TestClient, sample_entry: dict
    ) -> None:
        """Test update with no fields returns success."""
        create_response = client.post("/add_entry", json=sample_entry)
        entry_id = create_response.json()["entry_id"]

        update_data = {"id": entry_id}
        response = client.put("/update_entry", json=update_data)
        assert response.status_code == 200
        assert response.json()["entry_id"] == entry_id


class TestGetEntries:
    """Integration tests for /get_entries endpoint."""

    def test_get_entries_empty(self, client: TestClient) -> None:
        """Test getting entries when database is empty."""
        response = client.get("/get_entries")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["entries"] == []

    def test_get_entries_after_add(self, client: TestClient, sample_entry: dict) -> None:
        """Test retrieving entries after adding one."""
        client.post("/add_entry", json=sample_entry)
        response = client.get("/get_entries")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["meal"] == sample_entry["meal"]
        assert entry["stress"] == sample_entry["stress"]

    def test_get_entries_multiple(self, client: TestClient, sample_entry: dict) -> None:
        """Test retrieving multiple entries."""
        for i in range(3):
            entry = sample_entry.copy()
            entry["notes"] = f"entry {i}"
            client.post("/add_entry", json=entry)
        response = client.get("/get_entries")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["entries"]) == 3

    def test_get_entries_with_limit(self, client: TestClient, sample_entry: dict) -> None:
        """Test limit parameter."""
        for i in range(5):
            entry = sample_entry.copy()
            entry["notes"] = f"entry {i}"
            client.post("/add_entry", json=entry)
        response = client.get("/get_entries?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["entries"]) == 2

    def test_get_entries_with_offset(self, client: TestClient, sample_entry: dict) -> None:
        """Test offset parameter."""
        for i in range(5):
            entry = sample_entry.copy()
            entry["notes"] = f"entry {i}"
            client.post("/add_entry", json=entry)
        response = client.get("/get_entries?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_get_entries_response_structure(self, client: TestClient, sample_entry: dict) -> None:
        """Test response includes all required fields."""
        client.post("/add_entry", json=sample_entry)
        response = client.get("/get_entries")
        data = response.json()
        entry = data["entries"][0]
        required_fields = {
            "id",
            "date",
            "meal",
            "alcohol",
            "stress",
            "sleep_hours",
            "pain_level",
            "notes",
            "created_at",
        }
        assert set(entry.keys()) >= required_fields


class TestGetEntriesDateRange:
    """Integration tests for date range filtering in /get_entries."""

    def test_get_entries_with_start_date(self, client: TestClient) -> None:
        """Test filtering entries by start date."""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        entry1 = {
            "date": yesterday,
            "meal": "old entry",
            "alcohol": None,
            "stress": 3,
            "sleep_hours": 7,
            "pain_level": 1,
            "notes": "yesterday",
        }
        entry2 = {
            "date": today,
            "meal": "new entry",
            "alcohol": None,
            "stress": 2,
            "sleep_hours": 8,
            "pain_level": 0,
            "notes": "today",
        }

        client.post("/add_entry", json=entry1)
        client.post("/add_entry", json=entry2)

        response = client.get(f"/get_entries?start_date={today}")
        assert response.status_code == 200
        data = response.json()
        assert all(e["date"] >= today for e in data["entries"])

    def test_get_entries_with_end_date(self, client: TestClient) -> None:
        """Test filtering entries by end date."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        entry = {
            "date": yesterday,
            "meal": "past entry",
            "alcohol": None,
            "stress": 3,
            "sleep_hours": 7,
            "pain_level": 1,
            "notes": "old",
        }

        client.post("/add_entry", json=entry)

        response = client.get(f"/get_entries?end_date={yesterday}")
        assert response.status_code == 200
        data = response.json()
        assert all(e["date"] <= yesterday for e in data["entries"])

    def test_get_entries_with_date_range(self, client: TestClient) -> None:
        """Test filtering entries with both start and end date."""
        start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        end = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

        response = client.get(f"/get_entries?start_date={start}&end_date={end}")
        assert response.status_code == 200
        data = response.json()
        for entry in data["entries"]:
            assert start <= entry["date"] <= end

    def test_get_entries_invalid_start_date_format(self, client: TestClient) -> None:
        """Test that invalid start date format returns 422 (validation error)."""
        response = client.get("/get_entries?start_date=invalid-date")
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_get_entries_invalid_end_date_format(self, client: TestClient) -> None:
        """Test that invalid end date format returns 422 (validation error)."""
        response = client.get("/get_entries?end_date=2025/10/24")
        assert response.status_code == 422
        assert "detail" in response.json()


class TestSummarizeRecent:
    """Integration tests for /summarize_recent endpoint."""

    def test_summarize_recent_empty(self, client: TestClient) -> None:
        """Test summary with no entries."""
        response = client.get("/summarize_recent")
        assert response.status_code == 200
        data = response.json()
        assert data["window_days"] == 7
        assert data["summary"]["count"] == 0

    def test_summarize_recent_with_entries(self, client: TestClient, sample_entry: dict) -> None:
        """Test summary with entries in database."""
        client.post("/add_entry", json=sample_entry)
        response = client.get("/summarize_recent")
        assert response.status_code == 200
        data = response.json()
        assert data["window_days"] == 7
        summary = data["summary"]
        assert summary["count"] == 1
        assert summary["metrics"]["stress"]["avg"] == 4
        assert summary["metrics"]["sleep_hours"]["avg"] == 7.5
        assert summary["metrics"]["pain_level"]["avg"] == 2

    def test_summarize_recent_custom_window(self, client: TestClient, sample_entry: dict) -> None:
        """Test summary with custom window size."""
        client.post("/add_entry", json=sample_entry)
        response = client.get("/summarize_recent?window_days=30")
        assert response.status_code == 200
        data = response.json()
        assert data["window_days"] == 30

    def test_summarize_recent_response_structure(
        self, client: TestClient, sample_entry: dict
    ) -> None:
        """Test summary response has expected structure."""
        client.post("/add_entry", json=sample_entry)
        response = client.get("/summarize_recent")
        data = response.json()
        assert "window_days" in data
        assert "summary" in data
        summary = data["summary"]
        assert "count" in summary
        assert "metrics" in summary
        assert set(summary["metrics"].keys()) == {"stress", "sleep_hours", "pain_level"}

    def test_summarize_recent_filters_by_date(self, client: TestClient, sample_entry: dict) -> None:
        """Test that old entries are excluded from summary."""
        old_entry = sample_entry.copy()
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        old_entry["date"] = old_date
        old_entry["stress"] = 9
        client.post("/add_entry", json=old_entry)

        recent_entry = sample_entry.copy()
        recent_entry["stress"] = 3
        client.post("/add_entry", json=recent_entry)

        response = client.get("/summarize_recent?window_days=7")
        data = response.json()
        summary = data["summary"]
        assert summary["count"] == 1
        assert summary["metrics"]["stress"]["avg"] == 3

    def test_summarize_recent_multiple_entries(
        self, client: TestClient, sample_entry: dict
    ) -> None:
        """Test summary aggregates multiple entries correctly."""
        for stress_val in [2, 4, 6]:
            entry = sample_entry.copy()
            entry["stress"] = stress_val
            entry["notes"] = f"stress {stress_val}"
            client.post("/add_entry", json=entry)

        response = client.get("/summarize_recent")
        data = response.json()
        summary = data["summary"]
        assert summary["count"] == 3
        assert summary["metrics"]["stress"]["avg"] == 4.0
        assert summary["metrics"]["stress"]["min"] == 2
        assert summary["metrics"]["stress"]["max"] == 6


class TestPredictNextDay:
    """Integration tests for /predict_next_day endpoint."""

    def test_predict_next_day_insufficient_data(self, client: TestClient) -> None:
        """Test prediction endpoint returns 422 when there's insufficient data."""
        response = client.get("/predict_next_day?date=2025-10-24")
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_predict_next_day_with_sufficient_data(self, client: TestClient) -> None:
        """Test prediction endpoint returns prediction with sufficient historical data."""
        for i in range(10):
            day = 14 + i
            entry = {
                "date": f"2025-10-{day:02d}",
                "meal": "test meal",
                "stress": 3 + (i % 5),
                "sleep_hours": 7.0 + (i % 3),
                "pain_level": 2 + (i % 4),
            }
            client.post("/add_entry", json=entry)

        response = client.get("/predict_next_day?date=2025-10-24")
        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            assert "based_on_date" in data
            assert "prediction_for_date" in data
            assert data["based_on_date"] == "2025-10-24"
            assert data["prediction_for_date"] == "2025-10-25"
            assert "predicted_pain_level" in data
            assert "confidence" in data

            if data["predicted_pain_level"] is not None:
                assert 0 <= data["predicted_pain_level"] <= 10
                assert 0 <= data["confidence"] <= 1


class TestHealthEndpoint:
    """Integration tests for health check endpoints."""

    def test_root_endpoint(self, client: TestClient) -> None:
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200

    def test_health_endpoint(self, client: TestClient) -> None:
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestGetEntry:
    """Integration tests for /get_entry/{entry_id} endpoint."""

    def test_get_entry_success(self, client: TestClient, sample_entry: dict) -> None:
        """Test retrieving a single entry by ID."""
        add_response = client.post("/add_entry", json=sample_entry)
        assert add_response.status_code == 200
        entry_id = add_response.json()["entry_id"]

        response = client.get(f"/get_entry/{entry_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry_id
        assert data["date"] == sample_entry["date"]
        assert data["meal"] == sample_entry["meal"]

    def test_get_entry_not_found(self, client: TestClient) -> None:
        """Test that non-existent entry returns 404."""
        response = client.get("/get_entry/nonexistent-id-123")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestMCPEndpoint:
    """Integration tests for /mcp endpoint availability."""

    def test_mcp_endpoint_exists(self, client: TestClient) -> None:
        """Test that /mcp endpoint is mounted by fastapi_mcp."""
        response = client.get("/mcp")
        assert response.status_code in [400, 406], f"Unexpected status code: {response.status_code}"


class TestFeatureExtractionIntegration:
    """Integration tests for POST /entries/{entry_id}/extract_features endpoint."""

    @patch("personal_health.api.routes.extract_features_from_meal")
    def test_extraction_updates_database(self, mock_extract: MagicMock, client: TestClient) -> None:
        """Test that extracted features are persisted to database."""
        # Create an entry
        entry_data = {
            "date": "2025-11-05",
            "meal": "Grilled chicken salad with olive oil",
            "alcohol": "none",
            "stress": 3,
            "sleep_hours": 7.5,
            "pain_level": 2,
        }
        response = client.post("/add_entry", json=entry_data)
        assert response.status_code == 200
        entry_id = response.json()["entry_id"]

        # Mock extraction with comprehensive features
        mock_extract.return_value = ExtractedFeatures(
            features={
                "has_dairy": 0,
                "has_greens": 1,
                "is_fried": 0,
                "is_raw": 1,
                "has_coffee": 0,
                "has_alcohol": 0,
            },
            confidence={
                "has_dairy": "explicit",
                "has_greens": "explicit",
                "is_fried": "explicit",
                "is_raw": "inferred",
                "has_coffee": "explicit",
                "has_alcohol": "explicit",
            },
            reasoning={
                "has_dairy": "No dairy mentioned in salad",
                "has_greens": "Salad explicitly contains greens",
                "is_fried": "Grilled, not fried",
                "is_raw": "Salad vegetables are typically raw",
                "has_coffee": "No coffee mentioned",
                "has_alcohol": "Alcohol explicitly stated as none",
            },
        )

        # Call extraction endpoint
        extract_response = client.post(f"/entries/{entry_id}/extract_features")
        assert extract_response.status_code == 200
        extract_data = extract_response.json()

        # Verify response structure
        assert extract_data["entry_id"] == entry_id
        assert "features" in extract_data
        assert "confidence" in extract_data
        assert "reasoning" in extract_data

        # Verify extracted features in response
        assert extract_data["features"]["has_dairy"] == 0
        assert extract_data["features"]["has_greens"] == 1
        assert extract_data["features"]["is_fried"] == 0

        # Retrieve entry from database to verify persistence
        get_response = client.get(f"/get_entry/{entry_id}")
        assert get_response.status_code == 200
        stored_entry = get_response.json()

        # Verify features were persisted to database
        assert stored_entry["has_dairy"] == 0
        assert stored_entry["has_greens"] == 1
        assert stored_entry["is_fried"] == 0
        assert stored_entry["is_raw"] == 1
        assert stored_entry["has_coffee"] == 0
        assert stored_entry["has_alcohol"] == 0

        # Verify original entry data unchanged
        assert stored_entry["meal"] == entry_data["meal"]
        assert stored_entry["stress"] == entry_data["stress"]

    @patch("personal_health.api.routes.extract_features_from_meal")
    def test_extraction_with_user_profile(
        self, mock_extract: MagicMock, client: TestClient
    ) -> None:
        """Test extraction respects user profile context."""
        # Create user profile with dietary restrictions
        profile_data = {
            "dietary_restrictions": ["gluten-free", "vegan"],
            "allergies": ["peanuts"],
            "preferences": {"milk_type": "oat"},
            "habits": {"typical_breakfast": "oatmeal with oat milk"},
        }
        profile_response = client.put("/user/profile?user_id=test_user", json=profile_data)
        assert profile_response.status_code == 200

        # Create entry
        entry_data = {
            "date": "2025-11-05",
            "meal": "Oatmeal with milk",
            "stress": 2,
            "sleep_hours": 8,
            "pain_level": 1,
        }
        response = client.post("/add_entry", json=entry_data)
        entry_id = response.json()["entry_id"]

        # Mock extraction that uses profile context
        mock_extract.return_value = ExtractedFeatures(
            features={
                "has_dairy": 0,  # Oat milk, not dairy (inferred from profile)
                "is_gluten_free": 1,  # User is gluten-free
            },
            confidence={
                "has_dairy": "inferred",
                "is_gluten_free": "inferred",
            },
            reasoning={
                "has_dairy": "User prefers oat milk (profile), likely used oat milk",
                "is_gluten_free": "User is gluten-free, likely used GF oats",
            },
        )

        # Call extraction with user_id
        extract_response = client.post(f"/entries/{entry_id}/extract_features?user_id=test_user")
        assert extract_response.status_code == 200

        # Verify mock was called (should receive user profile)
        mock_extract.assert_called_once()
        call_args = mock_extract.call_args
        user_profile_arg = call_args[0][1]  # Second positional argument
        assert user_profile_arg.dietary_restrictions == ["gluten-free", "vegan"]
        assert user_profile_arg.preferences == {"milk_type": "oat"}

    @patch("personal_health.api.routes.extract_features_from_meal")
    def test_extraction_with_null_features(
        self, mock_extract: MagicMock, client: TestClient
    ) -> None:
        """Test that null (unknown) features are not written to database."""
        # Create entry
        entry_data = {
            "date": "2025-11-05",
            "meal": "Mystery meal",
            "stress": 2,
            "sleep_hours": 8,
            "pain_level": 1,
        }
        response = client.post("/add_entry", json=entry_data)
        entry_id = response.json()["entry_id"]

        # Mock extraction with mostly unknown features
        mock_extract.return_value = ExtractedFeatures(
            features={
                "has_dairy": None,  # Unknown
                "has_greens": 1,  # Known
                "is_fried": None,  # Unknown
                "has_coffee": 0,  # Known
            },
            confidence={
                "has_dairy": "unknown",
                "has_greens": "explicit",
                "is_fried": "unknown",
                "has_coffee": "explicit",
            },
            reasoning={
                "has_dairy": "Not enough information",
                "has_greens": "Mentioned in description",
                "is_fried": "Unclear from description",
                "has_coffee": "No coffee mentioned",
            },
        )

        # Call extraction
        extract_response = client.post(f"/entries/{entry_id}/extract_features")
        assert extract_response.status_code == 200

        # Verify database - only non-null features should be updated
        get_response = client.get(f"/get_entry/{entry_id}")
        stored_entry = get_response.json()

        # Known features should be set
        assert stored_entry["has_greens"] == 1
        assert stored_entry["has_coffee"] == 0

        # Unknown features should remain null (default)
        assert stored_entry["has_dairy"] is None
        assert stored_entry["is_fried"] is None

    def test_extraction_entry_not_found(self, client: TestClient) -> None:
        """Test extraction fails gracefully when entry doesn't exist."""
        response = client.post("/entries/nonexistent-id/extract_features")
        assert response.status_code == 404
        assert "Entry not found" in response.json()["detail"]

    @patch("personal_health.api.routes.extract_features_from_meal")
    def test_extraction_with_alcohol_features(
        self, mock_extract: MagicMock, client: TestClient
    ) -> None:
        """Test extraction handles alcohol-related features correctly."""
        # Create entry with alcohol
        entry_data = {
            "date": "2025-11-05",
            "meal": "Burger and fries",
            "alcohol": "2 IPAs",
            "stress": 4,
            "sleep_hours": 6.5,
            "pain_level": 3,
        }
        response = client.post("/add_entry", json=entry_data)
        entry_id = response.json()["entry_id"]

        # Mock extraction with alcohol features
        mock_extract.return_value = ExtractedFeatures(
            features={
                "has_alcohol": 1,
                "is_beer": 1,
                "is_wine": 0,
                "is_multiple_drinks": 1,
                "is_fried": 1,
                "has_dairy": 1,
            },
            confidence={
                "has_alcohol": "explicit",
                "is_beer": "explicit",
                "is_wine": "explicit",
                "is_multiple_drinks": "explicit",
                "is_fried": "inferred",
                "has_dairy": "inferred",
            },
            reasoning={
                "has_alcohol": "IPAs explicitly mentioned",
                "is_beer": "IPAs are beer",
                "is_wine": "Beer, not wine",
                "is_multiple_drinks": "2 IPAs = multiple drinks",
                "is_fried": "Fries are typically fried",
                "has_dairy": "Burger may contain cheese",
            },
        )

        # Extract features
        extract_response = client.post(f"/entries/{entry_id}/extract_features")
        assert extract_response.status_code == 200

        # Verify all alcohol features persisted
        get_response = client.get(f"/get_entry/{entry_id}")
        stored_entry = get_response.json()

        assert stored_entry["has_alcohol"] == 1
        assert stored_entry["is_beer"] == 1
        assert stored_entry["is_wine"] == 0
        assert stored_entry["is_multiple_drinks"] == 1

    @patch("personal_health.api.routes.extract_features_from_meal")
    def test_extraction_multiple_entries(self, mock_extract: MagicMock, client: TestClient) -> None:
        """Test extracting features for multiple different entries."""
        entries = [
            {
                "date": "2025-11-05",
                "meal": "Coffee and croissant",
                "stress": 2,
                "sleep_hours": 7,
                "pain_level": 1,
            },
            {
                "date": "2025-11-05",
                "meal": "Spicy tofu stir-fry with rice",
                "stress": 3,
                "sleep_hours": 7,
                "pain_level": 2,
            },
        ]

        # Create entries and extract features for each
        for i, entry_data in enumerate(entries):
            response = client.post("/add_entry", json=entry_data)
            entry_id = response.json()["entry_id"]

            # Different mock responses for different entries
            if i == 0:  # Coffee entry
                mock_extract.return_value = ExtractedFeatures(
                    features={"has_coffee": 1, "has_dairy": None, "is_gluten_free": 0},
                    confidence={
                        "has_coffee": "explicit",
                        "has_dairy": "unknown",
                        "is_gluten_free": "inferred",
                    },
                    reasoning={
                        "has_coffee": "Coffee explicitly mentioned",
                        "has_dairy": "May contain butter/milk",
                        "is_gluten_free": "Croissants contain gluten",
                    },
                )
            else:  # Tofu entry
                mock_extract.return_value = ExtractedFeatures(
                    features={"has_tofu": 1, "has_rice": 1, "is_spicy": 1, "is_fried": None},
                    confidence={
                        "has_tofu": "explicit",
                        "has_rice": "explicit",
                        "is_spicy": "explicit",
                        "is_fried": "unknown",
                    },
                    reasoning={
                        "has_tofu": "Tofu explicitly mentioned",
                        "has_rice": "Rice explicitly mentioned",
                        "is_spicy": "Spicy explicitly mentioned",
                        "is_fried": "Stir-fry could be various cooking methods",
                    },
                )

            # Extract features
            extract_response = client.post(f"/entries/{entry_id}/extract_features")
            assert extract_response.status_code == 200

        # Verify both entries have their unique features
        all_entries = client.get("/get_entries").json()["entries"]
        assert len(all_entries) == 2

        coffee_entry = next(e for e in all_entries if "coffee" in e["meal"].lower())
        tofu_entry = next(e for e in all_entries if "tofu" in e["meal"].lower())

        assert coffee_entry["has_coffee"] == 1
        assert coffee_entry["is_gluten_free"] == 0

        assert tofu_entry["has_tofu"] == 1
        assert tofu_entry["has_rice"] == 1
        assert tofu_entry["is_spicy"] == 1
