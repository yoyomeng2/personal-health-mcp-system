"""Feature extraction utilities for pain prediction model."""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class FeatureDefinition:
    """Definition of a binary feature with associated keywords."""

    name: str
    keywords: tuple[str, ...]
    exclude: tuple[str, ...] = ()
    check_combined: bool = False
    requires_alcohol: bool = False
    conjunction: tuple[str, ...] = ()


class PersonalHealthFeature(Enum):
    """Base class for personal health features."""


class LagFeature(PersonalHealthFeature):
    """Lag features for stress, sleep, and pain."""

    STRESS = "stress"
    SLEEP_HOURS = "sleep_hours"
    PAIN_LEVEL = "pain_level"


class RollingStatFeature(PersonalHealthFeature):
    """Rolling statistic features for stress, sleep, and pain."""

    AVERAGE_STRESS = FeatureDefinition(name="average_stress", keywords=())
    MAX_STRESS = FeatureDefinition(name="max_stress", keywords=())
    AVERAGE_SLEEP = FeatureDefinition(name="average_sleep", keywords=())
    MIN_SLEEP = FeatureDefinition(name="min_sleep", keywords=())
    AVERAGE_PAIN = FeatureDefinition(name="average_pain", keywords=())
    MAX_PAIN = FeatureDefinition(name="max_pain", keywords=())


class TemporalFeature(PersonalHealthFeature):
    """Temporal features related to the day of the week and time of day."""

    DAY_OF_WEEK = FeatureDefinition(name="day_of_week", keywords=())


class AlcoholFeature(PersonalHealthFeature):
    """Alcohol-related features with associated keyword patterns."""

    HAS_ALCOHOL = FeatureDefinition(name="has_alcohol", keywords=(), exclude=("none",))
    IS_BEER = FeatureDefinition(name="is_beer", keywords=("beer",))
    IS_WINE = FeatureDefinition(name="is_wine", keywords=("wine",))
    IS_MULTIPLE_DRINKS = FeatureDefinition(
        name="is_multiple_drinks",
        keywords=("several", "few", "multiple", "many", "couple", "handful"),
        requires_alcohol=True,
        conjunction=("and",),
    )


class SubstanceFeature(PersonalHealthFeature):
    """Substance-related features with associated keyword patterns."""

    HAS_THC = FeatureDefinition(name="has_thc", keywords=("thc", "cannabis"))


class MealFeature(PersonalHealthFeature):
    """Meal-related features with associated keyword patterns."""

    HAS_BEANS = FeatureDefinition(name="has_beans", keywords=("bean", "beans"))
    HAS_RICE = FeatureDefinition(name="has_rice", keywords=("rice",))
    HAS_PASTA = FeatureDefinition(name="has_pasta", keywords=("pasta",))
    HAS_TOFU = FeatureDefinition(name="has_tofu", keywords=("tofu",))
    HAS_NUTS = FeatureDefinition(
        name="has_nuts", keywords=("nut", "nuts", "almond", "walnut", "pecan", "cashew")
    )
    HAS_PEANUT = FeatureDefinition(name="has_peanut", keywords=("peanut", "peanuts"))
    IS_GLUTEN_FREE = FeatureDefinition(
        name="is_gluten_free", keywords=("gluten-free", "gluten free")
    )
    HAS_DAIRY = FeatureDefinition(
        name="has_dairy", keywords=("cheese", "yogurt", "milk", "creamer", "dairy", "cream")
    )
    IS_SPICY = FeatureDefinition(
        name="is_spicy",
        keywords=(
            "chili",
            "curry",
            "cajun",
            "spicy",
            "hot sauce",
            "jalapeño",
            "pepper",
        ),
    )
    IS_FRIED = FeatureDefinition(name="is_fried", keywords=("fried", "fries", "crispy", "chips"))
    IS_RAW = FeatureDefinition(name="is_raw", keywords=("sushi", "raw", "sashimi"))
    HAS_COFFEE = FeatureDefinition(name="has_coffee", keywords=("coffee",), check_combined=True)
    HAS_GREENS = FeatureDefinition(
        name="has_greens",
        keywords=("kale", "arugula", "chard", "bok choy", "greens", "spinach", "lettuce"),
    )
    HAS_CORN = FeatureDefinition(
        name="has_corn",
        keywords=(
            "corn",
            "tortilla",
            "taco",
            "chips",
            "maize",
            "polenta",
            "cornbread",
            "canola",
        ),
    )


def extract_meal_alcohol_features(meal: str | None, alcohol: str | None) -> list[float]:
    """Extract binary features from meal and alcohol text.

    Args:
        meal (str | None): Meal description text.
        alcohol (str | None): Alcohol consumption text.

    Returns:
        list[float]: List of 19 binary features (0.0 or 1.0).
    """
    meal_text = (meal or "").lower()
    alcohol_text = (alcohol or "").lower()
    combined_text = f"{meal_text} {alcohol_text}"

    features: list[float] = []

    # Extract alcohol features
    for alcohol_element in AlcoholFeature:
        value = _extract_feature_value(alcohol_text, combined_text, alcohol_element)
        features.append(value)

    # Track if alcohol is present for substance/meal features that need it
    has_alcohol = features[0] > 0.0

    # Extract substance features
    for substance_element in SubstanceFeature:
        value = _extract_feature_value(meal_text, combined_text, substance_element, has_alcohol)
        features.append(value)

    # Extract meal features
    for meal_element in MealFeature:
        value = _extract_feature_value(meal_text, combined_text, meal_element, has_alcohol)
        features.append(value)

    return features


def _extract_feature_value(
    text: str,
    combined_text: str,
    feature: PersonalHealthFeature,
    has_alcohol: bool = False,
) -> float:
    """Extract a single feature value from text.

    Args:
        text (str): The primary text to search (meal or alcohol).
        combined_text (str): Combined meal and alcohol text.
        feature (PersonalHealthFeature): The feature definition to extract.
        has_alcohol (bool, optional): Whether alcohol is present. Defaults to False.

    Returns:
        float: 1.0 if feature is present, 0.0 otherwise.
    """
    feature_def = feature.value

    search_text = combined_text if feature_def.check_combined else text

    # Check for exclusions first
    if feature_def.exclude and any(word in text for word in feature_def.exclude):
        return 0.0

    # Special case: has_alcohol (no keywords, just check if text exists and not excluded)
    if not feature_def.keywords:
        return 0.0 if not text or any(word in text for word in feature_def.exclude) else 1.0

    # Check if any keyword matches
    has_keyword = any(word in search_text for word in feature_def.keywords)

    # Special case: requires alcohol and conjunction
    if feature_def.requires_alcohol and feature_def.conjunction:
        has_conjunction = any(word in text for word in feature_def.conjunction)
        return 1.0 if has_keyword or (has_conjunction and has_alcohol) else 0.0

    return 1.0 if has_keyword else 0.0
