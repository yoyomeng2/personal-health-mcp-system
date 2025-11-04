"""Ollama-based feature extraction provider (stubbed for future implementation)."""

from personal_health.db.schemas import EntrySchema
from personal_health.logging_config import get_logger
from personal_health.ml.providers.base import ExtractedFeatures, LLMProvider, UserProfile

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama-based feature extraction (stubbed for future implementation)."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        """Initialize Ollama provider.

        Args:
            model (str): Ollama model name (e.g., "llama3.2:latest").
            base_url (str, optional): Ollama server URL. Defaults to "http://localhost:11434".
        """
        self.model = model
        self.base_url = base_url
        logger.warning("OllamaProvider is currently stubbed and not implemented")

    def extract_features(self, entry: EntrySchema, user_profile: UserProfile) -> ExtractedFeatures:
        """Extract features using Ollama (stubbed).

        TODO: Implement Ollama extraction using OpenAI-compatible API:
        - Use openai.OpenAI(base_url=f"{self.base_url}/v1")
        - Same prompt structure as OpenAI
        - Handle JSON mode differences if any

        Args:
            entry (EntrySchema): Database entry with meal, alcohol, and notes fields.
            user_profile (UserProfile): User's dietary profile for context.

        Returns:
            ExtractedFeatures: Extracted features with confidence and reasoning.

        Raises:
            NotImplementedError: Always raised as this is a stub.
        """
        raise NotImplementedError("OllamaProvider not yet implemented. Use OpenAIProvider for now.")
