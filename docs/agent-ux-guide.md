# Agent UX Guide for Personal Health System

This guide provides conversational patterns and workflows for AI agents helping users track health data, with emphasis on natural language interactions and intelligent feature extraction.

## Core Principles

- **Natural Language First**: Use conversational language, not technical feature names
- **Batch Confirmations**: Present multiple items for single confirmation, not question-by-question
- **Profile-Aware**: Leverage user dietary preferences for smarter extraction
- **Graceful Ambiguity**: Leave features null when uncertain, then ask clarifying questions
- **Violation Detection**: Notice when user behavior differs from their profile

## Workflow Overview

1. **Profile Onboarding** - First-time setup of dietary preferences
2. **Entry Creation** - Create entry, extract features, present for confirmation
3. **Clarification** - Handle null/ambiguous features with natural questions
4. **Updates** - Allow corrections and re-extraction as needed
5. **Profile Maintenance** - Check staleness and prompt updates

---

## 1. Profile Onboarding (First-Time Users)

If the user profile is empty or stale, guide through onboarding:

```text
Let's set up your dietary profile to improve meal tracking accuracy.

1. Do you have any dietary restrictions? (e.g., gluten-free, dairy-free, vegan, vegetarian)
2. Any food allergies we should know about? (e.g., peanuts, shellfish, tree nuts)
3. What type of milk do you typically use? (e.g., dairy, oat, almond, soy)
4. Any other food preferences or typical habits? (e.g., flour vs corn tortillas, typical breakfast)
```

**API Call:**

```text
mcp_personal-heal_update_user_profile(
    dietary_restrictions=["gluten-free", "lactose-intolerant"],
    allergies=["shellfish"],
    preferences={"milk_type": "oat", "tortilla_type": "flour"},
    habits={"typical_breakfast": "cereal with oat milk"}
)
```

---

## 2. Creating an Entry

When the user describes a meal:

### Step A: Create Entry

```text
mcp_personal-heal_add_entry(
    meal="burrito",
    date="2025-11-05",
    stress=5,
    sleep_hours=7.5,
    pain_level=3
)
```

### Step B: Extract Features

```text
mcp_personal-heal_extract_features(
    entry_id="<returned_entry_id>",
    user_id="default_user"
)
```

### Step C: Present Results

**For explicit features (high confidence):**

```text
✓ Your burrito included:
  • Flour tortilla (not corn, based on your usual preference)
  • Not gluten-free (flour tortilla)

I wasn't sure about:
  • Did it have beans?
  • Any cheese or dairy-free cheese?
  • Was it spicy?

Tell me what it had, or say 'none' if it didn't have any of these.
```

---

## 3. Batch Confirmation Format

### Present Explicit Features

Show what was confidently extracted with checkmarks:

```text
✓ Your [meal description] included:
  • Dairy (cheese mentioned)
  • Wheat (not gluten-free)
  • Fried (french fries)
```

### Present Ambiguous Features

Group null values as natural questions:

```text
I wasn't sure about:
  • Did it have beans?
  • Was it spicy?
  • Any greens like lettuce or spinach?

Tell me what it had, or say 'none' if it didn't have any of these.
```

### Accept Confirmations

- **"Yes" or "looks good"** → Accept all explicit features, leave nulls as-is
- **Specific corrections** → "actually it was gluten-free" or "it had beans too"
- **"None"** → Set all questioned features to 0

**API Call for Updates:**

```text
mcp_personal-heal_update_entry(
    id="<entry_id>",
    has_beans=1,
    is_spicy=1,
    has_greens=0
)
```

---

## 4. Profile-Based Inference

The LLM extraction uses user profile context for smarter inference:

### Example: Profile Context Inference

**User profile:**

- Dietary restrictions: gluten-free, lactose-intolerant
- Preferences: milk_type=oat, tortilla_type=flour

**User says:** "burrito"

**Extraction infers:**

- `has_corn: 0` (user uses flour tortillas, explicitly stored in profile)
- `has_dairy: null` (could have dairy-free cheese, need to ask)
- `has_beans: null` (common but not certain)

### Profile Violation Detection

If extraction detects behavior inconsistent with profile, ask for clarification:

```text
You had regular milk? That's unusual since you're lactose-intolerant and typically use oat milk.
Is that correct, or did you mean oat milk?
```

---

## 5. Handling Clarifications

### Good Clarification (Natural Language)

```text
A few quick questions about your pasta:
• Any cheese or dairy?
• Was it spicy?
• Did it have beans?
```

### Bad Clarification (Too Technical)

```text
Please specify values for: has_dairy, is_spicy, has_beans
```

### Grouping Strategy

- Group similar questions together (ingredients, preparation style, etc.)
- Make it easy to say "none" for everything
- Use bullet points for readability

---

## 6. Iteration and Updates

### User-Initiated Corrections

- Users can update entries anytime: `mcp_personal-heal_update_entry`
- Re-run extraction if meal description changes significantly
- Keep conversation natural, avoid repetitive confirmations

### Example

```text
User: "Actually, that pizza did have peppers on it"

Agent: "Got it! Updating your pizza to include greens. ✓"
[Calls: mcp_personal-heal_update_entry(id=<id>, has_greens=1)]
```

---

## 7. Profile Maintenance

### Check Staleness

```text
profile = mcp_personal-heal_get_user_profile(user_id="default_user")
if profile["profile_stale"]:
    # Prompt for review
```

### Prompt for Updates

```text
It's been a while since we reviewed your dietary profile. Has anything changed with your:
• Dietary restrictions?
• Allergies?
• Typical food preferences?

Let me know if you'd like to update anything.
```

**API Call:**

```text
mcp_personal-heal_update_user_profile(
    # Updated fields
)
```

---

## Complete Example Workflow

### User: "I had pizza today"

**Agent Actions:**

1. Create entry: `mcp_personal-heal_add_entry(meal="pizza", date="2025-11-05", ...)`
2. Extract features: `mcp_personal-heal_extract_features(entry_id=<id>)`
3. Present results:

```text
✓ Your pizza included:
  • Dairy (cheese)
  • Wheat (not gluten-free)

I wasn't sure about:
  • Was it spicy?
  • Any veggies like peppers or greens?

Tell me if it had any of these, or say 'no' if not.
```

### User: "it had peppers and was a little spicy"

**Agent Actions:**

1. Update entry: `mcp_personal-heal_update_entry(id=<id>, has_greens=1, is_spicy=1)`
2. Confirm: "Got it! Entry saved. ✓"

---

## Feature Reference

### Binary Features (19 total)

- **Meal Ingredients**: has_beans, has_rice, has_pasta, has_tofu, has_nuts, has_peanut, has_dairy, has_coffee, has_greens, has_corn
- **Preparation**: is_gluten_free, is_spicy, is_fried, is_raw
- **Alcohol**: has_alcohol, is_beer, is_wine, is_multiple_drinks
- **Substances**: has_thc

### Natural Language Mapping

When asking about features, use natural language:

- `has_dairy` → "Any cheese or dairy?"
- `is_spicy` → "Was it spicy?"
- `has_greens` → "Any greens like lettuce or spinach?"
- `is_gluten_free` → "Was it gluten-free?"

---

## API Reference

### Core MCP Tools

- `mcp_personal-heal_add_entry` - Create new entry
- `mcp_personal-heal_update_entry` - Update existing entry
- `mcp_personal-heal_get_entry` - Retrieve single entry
- `mcp_personal-heal_extract_features` - LLM-based feature extraction
- `mcp_personal-heal_get_user_profile` - Get user dietary profile
- `mcp_personal-heal_update_user_profile` - Update user profile

See API documentation at `/docs` endpoint for full schemas and parameters.
