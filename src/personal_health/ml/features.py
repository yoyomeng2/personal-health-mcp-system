"""Feature extraction utilities for pain prediction model."""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class FeatureDefinition:
    """Definition of a binary feature for training/prediction.

    The name field maps to the DB column name.
    The description is used in LLM prompts for feature extraction.
    """

    name: str
    description: str = ""


class PersonalHealthFeature(Enum):
    """Base class for personal health features."""


class LagFeature(PersonalHealthFeature):
    """Lag features for stress, sleep, and pain."""

    STRESS = "stress"
    SLEEP_HOURS = "sleep_hours"
    PAIN_LEVEL = "pain_level"


class RollingStatFeature(PersonalHealthFeature):
    """Rolling statistic features for stress, sleep, and pain."""

    AVERAGE_STRESS = FeatureDefinition(name="average_stress")
    MAX_STRESS = FeatureDefinition(name="max_stress")
    AVERAGE_SLEEP = FeatureDefinition(name="average_sleep")
    MIN_SLEEP = FeatureDefinition(name="min_sleep")
    AVERAGE_PAIN = FeatureDefinition(name="average_pain")
    MAX_PAIN = FeatureDefinition(name="max_pain")


class TemporalFeature(PersonalHealthFeature):
    """Temporal features related to the day of the week and time of day."""

    DAY_OF_WEEK = FeatureDefinition(name="day_of_week")


class AlcoholFeature(PersonalHealthFeature):
    """Alcohol-related features."""

    HAS_ALCOHOL = FeatureDefinition(name="has_alcohol", description="Contains alcohol")
    IS_BEER = FeatureDefinition(name="is_beer", description="Is beer")
    IS_WINE = FeatureDefinition(name="is_wine", description="Is wine")
    IS_MULTIPLE_DRINKS = FeatureDefinition(
        name="is_multiple_drinks", description="Multiple alcoholic drinks"
    )


class SubstanceFeature(PersonalHealthFeature):
    """Substance-related features."""

    HAS_THC = FeatureDefinition(name="has_thc", description="Contains THC/cannabis")


class MealFeature(PersonalHealthFeature):
    """Meal-related features."""

    HAS_BEANS = FeatureDefinition(
        name="has_beans", description="Contains beans (black, pinto, kidney, etc.)"
    )
    HAS_COFFEE = FeatureDefinition(name="has_coffee", description="Contains coffee")
    HAS_CORN = FeatureDefinition(name="has_corn", description="Contains corn")
    HAS_DAIRY = FeatureDefinition(
        name="has_dairy", description="Contains dairy (milk, cheese, yogurt, butter)"
    )
    HAS_GREENS = FeatureDefinition(name="has_greens", description="Contains leafy greens")
    HAS_NUTS = FeatureDefinition(name="has_nuts", description="Contains nuts (except peanuts)")
    HAS_PASTA = FeatureDefinition(name="has_pasta", description="Contains pasta/noodles")
    HAS_PEANUT = FeatureDefinition(name="has_peanut", description="Contains peanuts/peanut butter")
    HAS_RICE = FeatureDefinition(name="has_rice", description="Contains rice")
    HAS_TOFU = FeatureDefinition(name="has_tofu", description="Contains tofu")
    IS_GLUTEN_FREE = FeatureDefinition(name="is_gluten_free", description="Is gluten-free")
    IS_FRIED = FeatureDefinition(name="is_fried", description="Is fried/deep-fried")
    IS_RAW = FeatureDefinition(name="is_raw", description="Contains raw ingredients")
    IS_SPICY = FeatureDefinition(name="is_spicy", description="Is spicy")
