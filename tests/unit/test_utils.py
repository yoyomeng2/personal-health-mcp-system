"""Unit tests for utils module."""

from personal_health.utils import AGENT_UX_GUIDE, get_agent_ux_guide_content


class TestGetAgentUxGuideContent:
    """Unit tests for get_agent_ux_guide_content function."""

    def test_agent_ux_guide_path_exists(self) -> None:
        """Test that AGENT_UX_GUIDE constant points to an existing file."""
        assert AGENT_UX_GUIDE.exists(), (
            f"Agent UX guide file not found at: {AGENT_UX_GUIDE}\n"
            f"Expected the file to exist. Check the AGENT_UX_GUIDE path in utils.py."
        )

        # Verify it's actually a file, not a directory
        assert AGENT_UX_GUIDE.is_file(), f"Path exists but is not a file: {AGENT_UX_GUIDE}"

        # Verify it has content
        content = AGENT_UX_GUIDE.read_text(encoding="utf-8")
        assert len(content) > 0, "Agent UX guide file is empty"
        assert "# Agent UX Guide" in content, "Agent UX guide missing expected header"

    def test_returns_content_string(self) -> None:
        """Test that function returns non-empty string content."""
        content = get_agent_ux_guide_content()

        assert isinstance(content, str)
        assert len(content) > 0
