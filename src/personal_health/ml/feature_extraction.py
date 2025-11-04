"""LLM-based feature extraction from meal descriptions with user context."""

from __future__ import annotations

import os

from personal_health.config import Config
from personal_health.db.schemas import EntrySchema
from personal_health.logging_config import get_logger
from personal_health.ml.providers import (
    ExtractedFeatures,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
    UserProfile,
)

logger = get_logger(__name__)


def get_llm_provider() -> LLMProvider:
    """Factory function to get configured LLM provider.

    Returns:
        LLMProvider: Configured LLM provider instance.

    Raises:
        ValueError: If provider configuration is invalid.
    """
    config = Config()
    llm_config = config.get("llm", {})

    provider_name = llm_config.get("provider", "openai")
    model = llm_config.get("model", "gpt-4o-mini")
    temperature = llm_config.get("temperature", 0.0)
    max_tokens = llm_config.get("max_tokens", 1000)

    if provider_name == "openai":
        api_key_env = llm_config.get("api_key_env", "OPENAI_API_KEY")
        api_key = os.getenv(api_key_env)

        if not api_key:
            raise ValueError(f"OpenAI API key not found in environment variable: {api_key_env}")

        logger.debug(f"Using OpenAI provider with model: {model}")
        return OpenAIProvider(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    elif provider_name == "ollama":
        base_url = llm_config.get("base_url", "http://localhost:11434")
        logger.debug(f"Using Ollama provider with model: {model}")
        return OllamaProvider(model=model, base_url=base_url)

    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")


def extract_features_from_meal(entry: EntrySchema, user_profile: UserProfile) -> ExtractedFeatures:
    """Extract binary features from meal description using configured LLM.

    This is the main entry point for feature extraction.

    Args:
        entry (EntrySchema): Database entry with meal, alcohol, and notes fields.
        user_profile (UserProfile): User's dietary profile for context.

    Returns:
        ExtractedFeatures: Extracted features with confidence and reasoning.

    Raises:
        ValueError: If LLM provider configuration is invalid.
        Exception: If LLM extraction fails.
    """
    provider = get_llm_provider()
    return provider.extract_features(entry, user_profile)
