"""OpenAI-based feature extraction provider."""

import json

from openai import OpenAI

from personal_health.db.schemas import EntrySchema
from personal_health.logging_config import get_logger
from personal_health.ml.features import AlcoholFeature, MealFeature, SubstanceFeature
from personal_health.ml.providers.base import ExtractedFeatures, LLMProvider, UserProfile

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI-based feature extraction using structured output."""

    def __init__(self, model: str, api_key: str, temperature: float = 0.0, max_tokens: int = 1000):
        """Initialize OpenAI provider.

        Args:
            model (str): OpenAI model name (e.g., "gpt-4o-mini").
            api_key (str): OpenAI API key.
            temperature (float, optional): Sampling temperature. Defaults to 0.0.
            max_tokens (int, optional): Maximum tokens in response. Defaults to 1000.
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI(api_key=api_key)
        logger.info(f"Initialized OpenAI provider with model={model}")

    def extract_features(self, entry: EntrySchema, user_profile: UserProfile) -> ExtractedFeatures:
        """Extract features using OpenAI's structured output.

        Args:
            entry (EntrySchema): Database entry with meal, alcohol, and notes fields.
            user_profile (UserProfileRuntime): User's dietary profile for context.

        Returns:
            ExtractedFeatures: Extracted features with confidence and reasoning.

        """
        system_prompt = self._build_system_prompt(user_profile)
        user_prompt = self._build_user_prompt(entry)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        extracted = json.loads(content)

        return ExtractedFeatures(
            features=extracted.get("features", {}),
            confidence=extracted.get("confidence", {}),
            reasoning=extracted.get("reasoning", {}),
        )

    # REFACTOR: this should be in the base class since OllamaProvider will need it too
    def _build_system_prompt(self, user_profile: UserProfile) -> str:
        """Build system prompt with user profile context.

        Args:
            user_profile (UserProfileRuntime): User's dietary profile.

        Returns:
            str: System prompt with user context and extraction rules.
        """
        user_context = f"""USER PROFILE:
- Dietary Restrictions: {", ".join(user_profile.dietary_restrictions) if user_profile.dietary_restrictions else "None"}
- Allergies: {", ".join(user_profile.allergies) if user_profile.allergies else "None"}
- Preferences: {", ".join(user_profile.preferences) if user_profile.preferences else "None"}
- Habits: {", ".join(user_profile.habits) if user_profile.habits else "None"}"""

        # Build feature list from enums
        features = (
            [el.value for el in MealFeature]
            + [el.value for el in AlcoholFeature]
            + [el.value for el in SubstanceFeature]
        )
        feature_list = "\n".join(
            f"{i + 1}. {feat.name} - {feat.description}" for i, feat in enumerate(features)
        )
        feature_count = len(features)

        return f"""You are a food feature extraction assistant. Extract binary features from meal descriptions using the user's known dietary profile.

{user_context}

FEATURE EXTRACTION RULES:
- Return 1 (true) ONLY if explicitly stated OR clearly implied by user's known profile
- Return 0 (false) if explicitly absent OR conflicts with known profile
- Return null for ANY remaining ambiguity

FEATURES TO EXTRACT ({feature_count} binary features):
{feature_list}

CONFIDENCE LEVELS:
- "explicit": Directly stated or obvious from dish name
- "inferred": Likely based on user profile or common recipes
- "unknown": Not enough information

OUTPUT FORMAT (JSON):
{{
  "features": {{
    "has_beans": 1,
    "has_rice": null,
    ...
  }},
  "confidence": {{
    "has_beans": "explicit",
    "has_rice": "unknown",
    ...
  }},
  "reasoning": {{
    "has_beans": "Explicitly mentioned in description",
    "has_rice": "Not mentioned, common but not certain",
    ...
  }}
}}

Be conservative: prefer null over guessing."""

    def _build_user_prompt(self, entry: EntrySchema) -> str:
        """Build user prompt with entry information.

        Args:
            entry (EntrySchema): Database entry with meal, alcohol, and notes.

        Returns:
            str: Formatted user prompt with all available context.
        """
        parts = []

        if entry.meal:
            parts.append(f"MEAL: {entry.meal}")

        if entry.alcohol:
            parts.append(f"ALCOHOL: {entry.alcohol}")

        if entry.notes:
            parts.append(f"NOTES: {entry.notes}")

        entry_text = "\n".join(parts) if parts else "No description provided"

        # Calculate feature count dynamically
        feature_count = (
            len(list(MealFeature)) + len(list(AlcoholFeature)) + len(list(SubstanceFeature))
        )

        return f"""Extract features from this entry:

{entry_text}

Return JSON with features, confidence, and reasoning for each of the {feature_count} binary features."""
