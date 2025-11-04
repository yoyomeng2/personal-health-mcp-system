"""Unit tests for LLM-based feature extraction."""

from unittest.mock import MagicMock, patch

from personal_health.ml.feature_extraction import get_llm_provider


class TestGetLLMProvider:
    """Tests for LLM provider factory function."""

    @patch("personal_health.ml.feature_extraction.Config")
    @patch("personal_health.ml.feature_extraction.os.getenv")
    def test_get_openai_provider(self, mock_getenv: MagicMock, mock_config: MagicMock) -> None:
        """Test creating OpenAI provider with valid config."""
        # REFACTOR: make this a conftest fixture if more tests need it
        mock_config.return_value.get.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.0,
            "max_tokens": 1000,
            "api_key_env": "OPENAI_API_KEY",
        }
        mock_getenv.return_value = "test-api-key"

        provider = get_llm_provider()

        assert provider is not None
        assert hasattr(provider, "extract_features")
        mock_getenv.assert_called_once_with("OPENAI_API_KEY")

    @patch("personal_health.ml.feature_extraction.Config")
    def test_get_ollama_provider(self, mock_config: MagicMock) -> None:
        """Test creating Ollama provider with valid config."""
        # REFACTOR: make this a conftest fixture if more tests need it
        mock_config.return_value.get.return_value = {
            "provider": "ollama",
            "model": "llama2",
            "base_url": "http://localhost:11434",
        }

        provider = get_llm_provider()

        assert provider is not None
        assert hasattr(provider, "extract_features")
