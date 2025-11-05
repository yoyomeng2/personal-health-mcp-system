# type: ignore
"""Unit tests for LLM provider implementations."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from personal_health.db.schemas import EntrySchema
from personal_health.ml.features import AlcoholFeature, MealFeature, SubstanceFeature
from personal_health.ml.providers.base import ExtractedFeatures, UserProfile
from personal_health.ml.providers.openai import OpenAIProvider


@pytest.fixture
def sample_entry() -> EntrySchema:
    """Sample entry with all fields populated."""
    return EntrySchema(
        id="test-id",
        date="2024-01-01",
        meal="Pasta with marinara",
        alcohol="Glass of red wine",
        notes="Feeling good today",
        created_at="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_entry_meal_only() -> EntrySchema:
    """Sample entry with only meal field."""
    return EntrySchema(
        id="test-id",
        date="2024-01-01",
        meal="Black beans with rice",
        created_at="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_entry_alcohol_only() -> EntrySchema:
    """Sample entry with only alcohol field."""
    return EntrySchema(
        id="test-id",
        date="2024-01-01",
        alcohol="Beer",
        created_at="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_entry_empty() -> EntrySchema:
    """Sample entry with no meal/alcohol/notes."""
    return EntrySchema(
        id="test-id",
        date="2024-01-01",
        created_at="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def user_profile_full() -> UserProfile:
    """User profile with all fields populated."""
    return UserProfile(
        dietary_restrictions=["vegan", "gluten-free"],
        allergies=["peanuts", "shellfish"],
        preferences={"milk_type": "oat"},
        habits={"breakfast": "smoothie"},
    )


@pytest.fixture
def user_profile_empty() -> UserProfile:
    """User profile with empty fields."""
    return UserProfile(
        dietary_restrictions=[],
        allergies=[],
        preferences={},
        habits={},
    )


@pytest.fixture
def user_profile_vegan() -> UserProfile:
    """User profile for vegan user."""
    return UserProfile(
        dietary_restrictions=["vegan"],
        allergies=[],
        preferences={},
        habits={},
    )


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def test_init(self) -> None:
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider(
            model="gpt-4o-mini",
            api_key="test-key",
            temperature=0.5,
            max_tokens=500,
        )

        assert provider.model == "gpt-4o-mini"
        assert provider.temperature == 0.5
        assert provider.max_tokens == 500
        assert provider.client is not None

    def test_init_defaults(self) -> None:
        """Test OpenAI provider initialization with default parameters."""
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")

        assert provider.temperature == 0.0
        assert provider.max_tokens == 1000

    @patch("personal_health.ml.providers.openai.OpenAI")
    def test_extract_features_success(
        self,
        mock_openai_class: MagicMock,
        sample_entry_meal_only: EntrySchema,
        user_profile_vegan: UserProfile,
    ) -> None:
        """Test successful feature extraction."""
        # Setup mock response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content='{"features": {"has_beans": 1, "has_rice": 0}, '
                    '"confidence": {"has_beans": "explicit", "has_rice": "explicit"}, '
                    '"reasoning": {"has_beans": "Mentioned", "has_rice": "Not mentioned"}}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")
        provider.client = mock_client

        result = provider.extract_features(sample_entry_meal_only, user_profile_vegan)

        assert isinstance(result, ExtractedFeatures)
        assert result.features == {"has_beans": 1, "has_rice": 0}
        assert result.confidence == {"has_beans": "explicit", "has_rice": "explicit"}
        assert result.reasoning == {"has_beans": "Mentioned", "has_rice": "Not mentioned"}

        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4o-mini"
        assert call_args.kwargs["temperature"] == 0.0
        assert call_args.kwargs["max_tokens"] == 1000
        assert call_args.kwargs["response_format"] == {"type": "json_object"}
        assert len(call_args.kwargs["messages"]) == 2
        assert call_args.kwargs["messages"][0]["role"] == "system"
        assert call_args.kwargs["messages"][1]["role"] == "user"

    @patch("personal_health.ml.providers.openai.OpenAI")
    def test_extract_features_empty_response(
        self,
        mock_openai_class: MagicMock,
        sample_entry_meal_only: EntrySchema,
        user_profile_empty: UserProfile,
    ) -> None:
        """Test handling of empty response from OpenAI."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=None))]
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")
        provider.client = mock_client

        with pytest.raises(ValueError, match="Empty response from OpenAI"):
            provider.extract_features(sample_entry_meal_only, user_profile_empty)

    def test_build_system_prompt_with_full_profile(self, user_profile_full: UserProfile) -> None:
        """Test system prompt generation with complete user profile."""
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")

        prompt = provider._build_system_prompt(user_profile_full)

        # Check user profile section
        assert "USER PROFILE:" in prompt
        assert "vegan, gluten-free" in prompt
        assert "peanuts, shellfish" in prompt
        assert "milk_type" in prompt
        assert "breakfast" in prompt

        # Check feature extraction rules
        assert "FEATURE EXTRACTION RULES:" in prompt
        assert "Return 1 (true) ONLY if explicitly stated" in prompt
        assert "Return 0 (false) if explicitly absent" in prompt
        assert "Return null for ANY remaining ambiguity" in prompt

        # Check features are dynamically generated
        assert "FEATURES TO EXTRACT" in prompt
        feature_count = (
            len(list(MealFeature)) + len(list(AlcoholFeature)) + len(list(SubstanceFeature))
        )
        assert f"({feature_count} binary features)" in prompt

        # Check that feature descriptions are included
        assert "has_beans" in prompt
        assert "Contains beans" in prompt
        assert "has_alcohol" in prompt
        assert "Contains alcohol" in prompt

        # Check confidence levels
        assert "CONFIDENCE LEVELS:" in prompt
        assert '"explicit"' in prompt
        assert '"inferred"' in prompt
        assert '"unknown"' in prompt

        # Check output format
        assert "OUTPUT FORMAT (JSON):" in prompt
        assert "Be conservative: prefer null over guessing" in prompt

    def test_build_system_prompt_with_empty_profile(self, user_profile_empty: UserProfile) -> None:
        """Test system prompt generation with empty user profile."""
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")

        prompt = provider._build_system_prompt(user_profile_empty)

        # Check that "None" is used for empty fields
        assert "Dietary Restrictions: None" in prompt
        assert "Allergies: None" in prompt
        assert "Preferences: None" in prompt
        assert "Habits: None" in prompt

    def test_build_user_prompt_with_all_fields(self, sample_entry: EntrySchema) -> None:
        """Test user prompt generation with all entry fields."""
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")

        prompt = provider._build_user_prompt(sample_entry)

        assert "MEAL: Pasta with marinara" in prompt
        assert "ALCOHOL: Glass of red wine" in prompt
        assert "NOTES: Feeling good today" in prompt
        assert "Extract features from this entry:" in prompt

        feature_count = (
            len(list(MealFeature)) + len(list(AlcoholFeature)) + len(list(SubstanceFeature))
        )
        assert f"for each of the {feature_count} binary features" in prompt

    def test_build_user_prompt_with_only_meal(self, sample_entry_meal_only: EntrySchema) -> None:
        """Test user prompt generation with only meal field."""
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")

        prompt = provider._build_user_prompt(sample_entry_meal_only)

        assert "MEAL:" in prompt
        assert "Black beans with rice" in prompt
        assert "ALCOHOL:" not in prompt
        assert "NOTES:" not in prompt

    def test_build_user_prompt_with_only_alcohol(
        self, sample_entry_alcohol_only: EntrySchema
    ) -> None:
        """Test user prompt generation with only alcohol field."""
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")

        prompt = provider._build_user_prompt(sample_entry_alcohol_only)

        assert "ALCOHOL: Beer" in prompt
        assert "MEAL:" not in prompt
        assert "NOTES:" not in prompt

    def test_build_user_prompt_with_no_description(self, sample_entry_empty: EntrySchema) -> None:
        """Test user prompt generation with no meal/alcohol/notes."""
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")

        prompt = provider._build_user_prompt(sample_entry_empty)

        assert "No description provided" in prompt

    def test_feature_list_ordering(self, user_profile_empty: UserProfile) -> None:
        """Test that feature list is consistently ordered (Meal, Alcohol, Substance)."""
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")

        prompt = provider._build_system_prompt(user_profile_empty)

        # Extract the feature list section
        features_section = prompt.split("FEATURES TO EXTRACT")[1].split("CONFIDENCE LEVELS")[0]

        # Check that meal features come before alcohol features
        has_beans_pos = features_section.find("has_beans")
        has_alcohol_pos = features_section.find("has_alcohol")
        has_thc_pos = features_section.find("has_thc")

        assert has_beans_pos > 0  # Meal feature exists
        assert has_alcohol_pos > 0  # Alcohol feature exists
        assert has_thc_pos > 0  # Substance feature exists
        assert has_beans_pos < has_alcohol_pos  # Meal before Alcohol
        assert has_alcohol_pos < has_thc_pos  # Alcohol before Substance
