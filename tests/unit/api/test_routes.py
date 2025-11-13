"""Unit tests for API routes.

These are TRUE unit tests that mock external dependencies.
For integration tests that use real database operations, see tests/integration/api/test_routes.py
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from personal_health.api.dependencies import get_user_profile_repo
from personal_health.core import create_app


class TestUserProfileErrorHandling:
    """Unit tests for /user/profile endpoint error handling."""

    def test_get_user_profile_creation_failure(self, client: TestClient) -> None:
        """Test GET profile handles failure to create default profile."""
        # Create a new app with mocked user_profile_repo
        app = create_app()
        mock_repo = MagicMock()
        mock_repo.get.return_value = None
        mock_repo.create_or_update.return_value = None
        app.dependency_overrides[get_user_profile_repo] = lambda: mock_repo

        # Create a new client with the mocked app
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/user/profile?user_id=fail_user")
            assert response.status_code == 500
            assert "Failed to retrieve user profile" in response.json()["detail"]


class TestExtractFeatures:
    """Unit tests for POST /entries/{entry_id}/extract_features endpoint."""

    @patch("personal_health.api.routes.extract_features_from_meal")
    def test_extract_features_success(self, mock_extract: MagicMock, client: TestClient) -> None:
        """Test successful feature extraction from entry (mocked LLM)."""
        # Create an entry first
        entry_data = {
            "date": "2025-11-04",
            "meal": "Oatmeal with almond milk",
            "alcohol": "none",
            "stress": 2,
            "sleep_hours": 7.5,
            "pain_level": 1,
        }
        response = client.post("/add_entry", json=entry_data)
        assert response.status_code == 200
        entry_id = response.json()["entry_id"]

        # Mock the extraction response
        from personal_health.ml.providers.base import ExtractedFeatures

        mock_extract.return_value = ExtractedFeatures(
            features={"has_dairy": 0, "is_gluten_free": 1},
            confidence={"has_dairy": "explicit", "is_gluten_free": "inferred"},
            reasoning={
                "has_dairy": "Almond milk is dairy-free",
                "is_gluten_free": "Oatmeal typically contains gluten",
            },
        )

        # Call extraction endpoint
        response = client.post(f"/entries/{entry_id}/extract_features")
        assert response.status_code == 200

        data = response.json()
        assert data["entry_id"] == entry_id
        assert data["features"]["has_dairy"] == 0
        assert data["features"]["is_gluten_free"] == 1
        assert data["confidence"]["has_dairy"] == "explicit"
        assert "reasoning" in data

    def test_extract_features_entry_not_found(self, client: TestClient) -> None:
        """Test extraction fails when entry doesn't exist."""
        response = client.post("/entries/nonexistent-id/extract_features")
        assert response.status_code == 404
        assert "Entry not found" in response.json()["detail"]


class TestAgentUXGuide:
    """Unit tests for agent UX guide endpoint."""

    @patch("personal_health.api.routes.get_agent_ux_guide_content")
    def test_get_agent_ux_guide_calls_utils(
        self, mock_get_content: MagicMock, client: TestClient
    ) -> None:
        """Test that endpoint calls get_agent_ux_guide_content from utils."""
        mock_get_content.return_value = "# Agent UX Guide\n\nMocked content"
        response = client.get("/agent_ux_guide")

        assert response.status_code == 200
        assert "Mocked content" in response.json()["content"]
