# Project phases and remaining work

This file lists the remaining phases for the Personal Health MCP System, acceptance criteria, key files to edit, rough time estimates, and example commands. Use it as a living checklist while you develop.

- [Project phases and remaining work](#project-phases-and-remaining-work)
  - [Completed so far](#completed-so-far)
  - [Phase 3 — Testing and quality ✅](#phase-3--testing-and-quality-)
  - [Phase 4 — MCP layer (discovery + invoke) ✅](#phase-4--mcp-layer-discovery--invoke-)
  - [Phase 5 — Improvements to Summary \& Analysis ✅](#phase-5--improvements-to-summary--analysis-)
  - [Phase 6 — Model training \& prediction pipeline ✅](#phase-6--model-training--prediction-pipeline-)
  - [Phase 7 - Ingredient Feature Storage \& Hybrid Extraction](#phase-7---ingredient-feature-storage--hybrid-extraction)
  - [Phase 8 — Security, auth, and operational hygiene](#phase-8--security-auth-and-operational-hygiene)
  - [Phase 9 — CI/CD, packaging \& release](#phase-9--cicd-packaging--release)
  - [Phase 10 — Documentation \& Agent contract](#phase-10--documentation--agent-contract)
  - [Phase 11 — Polish, telemetry, and roadmap items](#phase-11--polish-telemetry-and-roadmap-items)
  - [How to use this file](#how-to-use-this-file)

## Completed so far

- Phase 0: README + agent guidance (scaffolded and documented) ✅
- Phase 1: Basic REST endpoints and scaffold (FastAPI app, DB, models, logging, config) ✅
- Phase 2: Analysis summary implemented (`/summarize_recent`) and verified against the local SQLite DB ✅
- Phase 3: Testing and quality ✅
- Phase 4: MCP layer (discovery + invoke) ✅
- Phase 5: Improvements to Summary & Analysis ✅
- Phase 6: Model training & prediction pipeline ✅

---

## Phase 3 — Testing and quality ✅

- Goal: Add unit tests and CI checks to protect core functionality.
- Acceptance criteria:
  - Unit tests exist for `compute_summary()`, DB helpers, and main route handlers (happy path + one edge case).
  - `pytest` runs locally and in CI with coverage for core modules.
  - `ruff` and `mypy` run as part of pre-commit or CI and pass (or have documented exceptions).
- Key files to add/edit:
  - `tests/unit/test_analysis.py` (tests for `compute_summary`)
  - `tests/unit/test_routes.py` (route tests or integration with TestClient)
  - `.github/workflows/ci.yaml` (CI workflow to run tests + linters)
- Rough estimate: 1–3 hours
- Commands:

```bash
uv run pytest --maxfail=1 -q
# Project phases and remaining work

This file lists the remaining phases for the Personal Health MCP System, acceptance criteria, key files to edit, rough time estimates, and example commands. Use it as a living checklist while you develop.

## Completed so far

- Phase 0: README + agent guidance (scaffolded and documented)

- Phase 1: Basic REST endpoints and scaffold (FastAPI app, DB, models, logging, config)

- Phase 2: Analysis summary implemented (`/summarize_recent`) and verified against the local SQLite DB

---

## Phase 3 — Testing and quality

- Goal: Add unit tests and CI checks to protect core functionality.

- Acceptance criteria:

  - Unit tests exist for `compute_summary()`, DB helpers, and main route handlers (happy path + one edge case).

  - `pytest` runs locally and in CI with coverage for core modules.

  - `ruff` and `mypy` run as part of pre-commit or CI and pass (or have documented exceptions).

- Key files to add/edit:

  - `tests/unit/test_analysis.py` (tests for `compute_summary`)

  - `tests/unit/test_routes.py` (route tests or integration with TestClient)

  - `.github/workflows/ci.yaml` (CI workflow to run tests + linters)

- Rough estimate: 1–3 hours

- Commands:

```bash
uv run pytest --maxfail=1 -q
uv run ruff check src tests
uv run mypy src
```

---

## Phase 4 — MCP layer (discovery + invoke) ✅

- Goal: Expose a machine-first MCP surface on top of REST so agents can discover and call functions reliably.

- Acceptance criteria:

  - `GET /mcp/discover` returns a machine-readable catalog of functions (name, version, input_schema, output_schema).

  - `POST /mcp/invoke` accepts `{"name":"<fn>", "args":{...}, "dry_run": bool, "idempotency_key": "..."}` and dispatches to registered handlers.

  - Audit logs and idempotency storage exist (simple file-based or DB table).

- Files to add/edit:

  - `src/personal_health/mcp/registry.py` (function registry)

  - `src/personal_health/mcp/invoke.py` (handlers for discover & invoke) or update `routes.py`

  - `data/logs/mcp_calls.log` (audit log path)

- Estimate: 2–4 hours

---

## Phase 5 — Improvements to Summary & Analysis ✅

- Goal: Improve metrics and reliability of `compute_summary` and prepare for EDA (Exploratory Data Analysis).

- Acceptance criteria:

  - Add get_entry by entry_id for precise retrieval.
  - Add get_entries filtering by date range to support flexible summaries.
  - Add median and standard deviation to metric output.
  - Handle missing or malformed dates gracefully and log warnings.
  - Provide a CSV export utility for quick EDA (scripts/export_summary.py).

- Files to edit or create:

  - `src/personal_health/mcp/analysis.py`
  - `src/personal_health/mcp/routes.py`
  - `src/personal_health/scripts/export_summary.py`

- Estimate: 1–2 hours

---

## Phase 6 — Model training & prediction pipeline ✅

- Goal: Implement a repeatable local model training pipeline and inference integration.

- Detail:

  - The main goal of this project is centered here, which is to predict if pain is associated with certain meals, ingredients, alcohol, stress, or sleep patterns based on historical data. This involves building a machine learning model that can analyze past entries and provide predictions for future pain levels.
  - A predictor will help inform future correlation between different factors and pain levels, enabling users to make more informed decisions about their health habits.
  - The correlation matrix endpoint will provide insights into how different ingredients and factors relate to pain levels, assisting in exploratory data analysis (EDA) for users to understand potential triggers.

- Approach:

  - Start simple with a baseline model that attempts to predict next-day pain levels based on historical entries using features like meal ingredients, alcohol consumption, stress levels, and sleep duration.
    - The model will be trained on existing data and integrated into the MCP system for predictions.
  - A correlation feature will require advancing the data schema to support ingredient-level analysis, possibly involving additional tables or data processing steps to extract ingredients from meal descriptions - see [Phase 7 - Ingredient Feature Storage & Hybrid Extraction](#phase-7---ingredient-feature-storage--hybrid-extraction) for more info.

- Acceptance criteria:

  - `src/personal_health/models/train.py` trains a baseline model and saves `data/model_v1.pkl`.
  - `src/personal_health/models/predictor.py` loads the model on startup (or lazily) and returns predictions.
  - `/predict_next_day` endpoint returns predictions of next day pain based on prior entries and confidence.
  - Validations to ensure data quality before training (e.g., minimum number of entries, 1 to 10 for scales with 0 being no data, etc.) are added

- Files to edit:

  - `src/personal_health/models/train.py` (feature engineering and training)
  - `src/personal_health/models/predictor.py` (loading + predict API)
  - `src/personal_health/mcp/routes.py` (use predictor)

- Estimate: 2–6 hours (depends on feature engineering complexity)

- Example local run:

```bash
uv run python -m src.personal_health.models.train
curl localhost:8080/predict_next_day?date=2025-10-24
# after second pass
curl localhost:8080/correlations
```

---

## Phase 7 - Ingredient Feature Storage & Hybrid Extraction

- Goal: Shift to a feature store pattern by gathering binary meal/alcohol features for storage the database and implement ingredient extraction (LLM inference + agent clarification) for higher quality training data.

- Approach:

  - **Problem**: Current keyword-based feature extraction is brittle, happens at prediction time, and model performance is limited by insufficient data (~84 samples for 48 features).
  - **Solution**: Store features directly in the database, enriched at entry creation time using:
    1. **LLM** - Extract explicitly mentioned ingredients, and infer likely ingredients from dish names with confidence scores
    2. **Agent** - Ask clarifying questions for ambiguous/missing features
  - This shifts from runtime extraction to an ETL/feature store pattern, improving data quality and model inputs.

- Acceptance criteria:

  - Create `user_profile` table with dietary preferences schema:
    - `dietary_restrictions` (JSON array): ["gluten-free", "lactose-intolerant", "vegan", "vegetarian", etc.]
    - `allergies` (JSON array): ["peanuts", "tree nuts", "shellfish", etc.]
    - `preferences` (JSON object): {"milk_type": "oat", "tortilla_type": "flour", "protein_preference": "tofu"}
    - `habits` (JSON object): {"typical_breakfast": "cereal with oat milk", "drinks_coffee_with": "oat creamer"}
    - `created_at`, `updated_at` timestamps
  - Add onboarding flow with initial questions:
    - "Do you have any dietary restrictions? (gluten-free, dairy-free, vegan, etc.)"
    - "Any food allergies we should know about?"
    - "What type of milk do you typically use?"
    - "Any other food preferences or habits?"
  - Implement `GET/PUT /user/profile` endpoints to manage profile
  - Extend `entries` table schema with 19 binary feature columns (nullable integers: 0, 1, or NULL).
  - Update API GET endpoints to return feature columns alongside meal/alcohol text.
  - Implement LLM-based extraction pipeline with user context:
    - LLM receives user profile in system prompt for context-aware extraction
    - Mark as 1 ONLY if explicitly stated or in known profile
    - Mark as 0 if explicitly absent OR conflicts with known profile
    - Use null for ANY remaining ambiguity
    - LLM provides both extracted features and suggested inferences with reasoning
  - Add `PATCH /entries/{entry_id}/features` endpoint to update feature values.
  - Agent presents batch confirmation:
    - Shows explicit features (high confidence)
    - Lists suggested inferences with reasoning
    - Allows single "yes" confirmation or specific corrections
  - Agent detects profile violations and asks clarifying questions:
    - "You had regular milk? That's unusual since you typically use oat milk."
  - Update model training to use stored features instead of text-based extraction.
  - Implement `/analyze_pain_triggers` endpoint to return feature correlations with pain levels.

- Files to edit or create:

  - `src/personal_health/db/schema.sql` - Add user_profile table and feature columns to entries
  - `src/personal_health/db/migrations/` - Migration scripts for new tables
  - `src/personal_health/api/schemas.py` - Add UserProfile, DietaryPreferences models
  - `src/personal_health/ml/extraction.py` - LLM-based extraction with user context
  - `src/personal_health/api/routes.py` - Add profile endpoints, update GET/PATCH for entries
  - `scripts/train_model.py` - Use stored features instead of runtime extraction
  - `tests/unit/test_extraction.py` - Test LLM extraction with profile context
  - `tests/unit/test_profile.py` - Test profile management

- Implementation steps:

  1. ✅ Schema migration: Create user_profile table with dietary preference fields
  2. ✅ Implement onboarding flow with initial dietary questions
  3. ✅ Add GET/PUT /user/profile endpoints
  4. Extend entries table with 19 feature columns
  5. Implement LLM extraction with user context injection
  6. Update API to expose features and accept PATCH updates
  7. Implement batch confirmation UX in agent prompts
  8. Add profile violation detection and clarifying questions
  9. Refactor model training to read features from DB columns
  10. Add correlation analysis endpoint

- Estimate: 8–12 hours (user profile schema, onboarding, context-aware extraction, API updates, testing)

- Example workflow:

```bash
# First-time user: Onboarding flow
# Agent: "Let's set up your dietary profile to improve accuracy.
#         Do you have any dietary restrictions? (gluten-free, dairy-free, vegan, etc.)"
# User: "I'm gluten-free and lactose-intolerant"
# Agent: "What type of milk do you typically use?"
# User: "Oat milk"
# Agent: "Any food allergies?"
# User: "No"

# Profile stored:
curl -X PUT localhost:8080/user/profile \
  -H "Content-Type: application/json" \
  -d '{
    "dietary_restrictions": ["gluten-free", "lactose-intolerant"],
    "preferences": {"milk_type": "oat", "tortilla_type": "flour"},
    "allergies": []
  }'

# Later: User creates entry
# Agent: "What did you eat?"
# User: "burrito"

# System runs context-aware LLM extraction:
prompt = """
USER DIETARY CONTEXT:
- Gluten-free diet
- Lactose-intolerant
- Typically uses oat milk
- Typically uses flour tortillas

Extract features from: "burrito"

EXPLICIT features (stated or obvious from context):
- has_corn: 0 (user uses flour tortillas, gluten-free)

INFERRED features (likely but not certain):
- has_beans: null (common but not stated)
- has_dairy: null (user is lactose-intolerant, but could have dairy-free cheese)
- is_spicy: null (not mentioned)
"""

# API returns:
{
  "date": "2025-11-03",
  "meal": "burrito",
  "has_corn": 0,        # Confident from profile
  "has_beans": null,    # Still ambiguous
  "has_dairy": null,    # Could be dairy-free alternative
  "is_spicy": null      # Unknown
}

# Agent batch confirmation:
# "Your burrito used flour tortilla (based on your usual preference). ✓
#  
#  I'm not sure about:
#  • Did it have beans?
#  • Any cheese or dairy-free cheese?
#  • Was it spicy?
#  
#  Tell me what it had, or say 'none' if it didn't have any of these."

# User: "black beans and dairy-free cheese, not spicy"

# Agent calls PATCH /entries/{id}/features:
curl -X PATCH localhost:8080/entries/abc123/features \
  -H "Content-Type: application/json" \
  -d '{"has_beans": 1, "has_dairy": 0, "is_spicy": 0}'

# Profile violation example:
# User: "had cereal with regular milk"
# Agent: "You had regular milk? That's unusual since you're lactose-intolerant.
#         Is that correct or did you mean oat milk?"

# Model training now uses complete, high-quality feature data with profile context
uv run train-model --db data/health.db
```

---

## Phase 8 — Security, auth, and operational hygiene

- Goal: Protect write operations and add operational controls.

- Acceptance criteria:

  - Implement API key or token-based auth for MCP write operations.
  - Add proper logging for security events, and ensure no secrets are logged.

- Files to edit:

  - `src/personal_health/mcp/routes.py` (auth checks)
  - `src/personal_health/config.py` (auth config)
  - `.github/workflows/ci.yaml` (secret scanning)

- Estimate: 2–4 hours

---

## Phase 9 — CI/CD, packaging & release

- Goal: Prepare build, test, and publishing workflows.

- Acceptance criteria:

  - CI runs tests, linters, and packaging steps.
  - `pyproject.toml` is finalized and package builds cleanly with hatchling (or chosen backend).
  - Releases can be produced from tags and optionally uploaded to an artifact store.

- Files to add/edit:

  - `.github/workflows/release.yaml`
  - `pyproject.toml` (finalize metadata)

- Estimate: 2–6 hours (depends on automation detail)

---

## Phase 10 — Documentation & Agent contract

- Goal: Produce clear docs for human contributors and machine-readable contract for agents.

- Acceptance criteria:

  - OpenAPI/Swagger docs auto-generated at `/docs` endpoint for agent consumption
  - `.github/copilot-instructions.md` updated with operational rules and agent examples
  - README has quickstart, MCP integration, and troubleshooting sections

- Files updated:

  - `README.md` (MCP integration section, idempotency behavior)
  - `.github/copilot-instructions.md` (already exists with project guidelines)

- Estimate: 2–4 hours

---

## Phase 11 — Polish, telemetry, and roadmap items

- Goal: Final polish: telemetry/metrics, performance checks, and a roadmap for future features.

- Possible additions:

  - Metrics (Prometheus) endpoint or simple counters logged to file.
  - Backend swap option (DuckDB) for analytics workloads.
  - UI/CLI for interactive entry creation and visualization.

- Estimate: ongoing / future work

---

## How to use this file

- Treat phases as checkpoints; complete one phase fully before moving to the next to keep scope small.
- Open a new git branch per phase and create a PR with tests and CI passing.
- If you want, tell me which phase to implement next and I will implement it and run quick checks locally.

---

Last updated: 2025-10-24
