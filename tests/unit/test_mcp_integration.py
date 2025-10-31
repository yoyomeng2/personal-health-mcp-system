"""Unit tests for MCP integration layer.

These tests verify MCP-specific functionality.

All REST endpoint behavior is tested in test_routes.py.
"""

from fastapi.testclient import TestClient


class TestMCPEndpoint:
    """Tests for /mcp endpoint availability."""

    def test_mcp_endpoint_exists(self, client: TestClient) -> None:
        """Test that /mcp endpoint is mounted by fastapi_mcp."""
        # MCP endpoint uses SSE protocol, so regular GET will fail
        # but we can verify it exists by checking it doesn't 404
        response = client.get("/mcp")
        # Should not be 404 (endpoint exists)
        # Will likely be 400/406 due to missing MCP protocol headers
        assert response.status_code in [400, 406], f"Unexpected status code: {response.status_code}"
