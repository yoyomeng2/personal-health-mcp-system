# Project phases and remaining work

This file lists the remaining phases for the Personal Health MCP System, acceptance criteria, key files to edit, rough time estimates, and example commands. Use it as a living checklist while you develop.

- [Project phases and remaining work](#project-phases-and-remaining-work)
  - [Completed so far](#completed-so-far)
  - [Phase 3 — Testing and quality ✅](#phase-3--testing-and-quality-)
  - [Phase 4 — MCP layer (discovery + invoke) ✅](#phase-4--mcp-layer-discovery--invoke-)
  - [Phase 5 — Improvements to Summary \& Analysis ✅](#phase-5--improvements-to-summary--analysis-)
  - [Phase 6 — Model training \& prediction pipeline ✅](#phase-6--model-training--prediction-pipeline-)
  - [Phase 7 — Security, auth, and operational hygiene](#phase-7--security-auth-and-operational-hygiene)
  - [Phase 8  - Model enhancements for Correlation Analysis](#phase-8----model-enhancements-for-correlation-analysis)
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
  - A correlation feature will require advancing the data schema to support ingredient-level analysis, possibly involving additional tables or data processing steps to extract ingredients from meal descriptions - see [Phase 8 - Model enhancements for Correlation Analysis](#phase-8----model-enhancements-for-correlation-analysis) for more info.

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

## Phase 7 — Security, auth, and operational hygiene

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

## Phase 8  - Model enhancements for Correlation Analysis

- Goal: Enhance the model to support ingredient-level correlation analysis.

- Acceptance criteria:

  - Update the data schema to support ingredient-level analysis (e.g., new tables for ingredients).
  - Implement feature extraction to parse meals into ingredients.
  - Update the model training pipeline to include ingredient, pain, stress, and sleep features.
- Implement `/analyze_pain_triggers` endpoint to return feature correlations with pain levels.

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
