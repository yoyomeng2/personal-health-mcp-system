# Personal Health MCP System  

A modular, local-first system to log, analyze, and predict personal health correlations using an MCP interface.  
Focus: food, alcohol, stress, sleep, and symptom tracking.

Note that this project is for educational purposes and not for production use.

- [Personal Health MCP System](#personal-health-mcp-system)
  - [1. Objective](#1-objective)
  - [2. Architecture Overview](#2-architecture-overview)
  - [3. Folder Layout](#3-folder-layout)
  - [4. Database Schema](#4-database-schema)
  - [5. Getting Started](#5-getting-started)
    - [Installation](#installation)
    - [Database Setup](#database-setup)
    - [Run the Server](#run-the-server)
    - [Run Tests](#run-tests)
    - [Code Quality](#code-quality)
  - [6. MCP Integration](#6-mcp-integration)
    - [Overview](#overview)
    - [Quick Start with ChatGPT](#quick-start-with-chatgpt)
    - [Idempotency](#idempotency)
    - [Documentation](#documentation)
  - [7. Model Pipeline](#7-model-pipeline)
    - [Model Selection](#model-selection)
    - [Feature Engineering](#feature-engineering)
    - [Metrics Used](#metrics-used)
      - [R-squared Score History](#r-squared-score-history)
    - [Expanded Learning Techniques](#expanded-learning-techniques)
      - [Different Model Types](#different-model-types)
    - [Expanded Scoring Techniques](#expanded-scoring-techniques)
  - [8. Example Workflow](#8-example-workflow)
  - [9. Optional Integrations](#9-optional-integrations)
  - [10. Next Steps](#10-next-steps)

---

## 1. Objective

Enable a local or agent-based system to:

- Log health and lifestyle data via controlled MCP calls.
- Query summaries, correlations, and predictions.
- Serve as the data backbone for ML-driven personal insight.

---

## 2. Architecture Overview

1. **Database Layer:** SQLite for structured health logs.  
2. **MCP Server:** FastAPI application exposing standardized methods.  
3. **Model Engine:** Random Forest Regressor (scikit-learn) for pain prediction.
4. **Agent Interface:** Local LLM or automation client consuming the MCP API.

```text
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ User Input   │──────▶│ MCP Server   │──────▶│ SQLite / ML  │
│ (Agent)      │       │ (FastAPI)    │       │ Engine       │
└──────────────┘       └──────────────┘       └──────────────┘
```

See [docs/architecture.md](docs/architecture.md) for detailed architecture diagrams and component descriptions.

---

## 3. Folder Layout

```text
personal-health-mcp-system/
├── pyproject.toml                      # Python project settings and dependencies
├── README.md                           # Project documentation
├── uv.lock                             # UV lockfile
├── configs/                            # Configuration files
│   ├── personal_health.yaml            # Default application configuration
│   └── environments/                   # Environment-specific configs
│       ├── dev.yaml
│       └── prod.yaml
├── data/                               # Runtime data (gitignored except structure)
│   ├── health.db                       # SQLite database
│   ├── model_v1.pkl                    # Trained ML model
│   └── logs/                           # Application logs
│       └── personal_health.log
├── docs/                               # Documentation
│   └── phases.md                       # Project phases and roadmap
├── scripts/                            # Utility scripts (see scripts/README.md)
│   ├── __init__.py
│   ├── README.md                       # Scripts documentation
│   ├── export_sqlite_to_csv.py         # Export database to CSV
│   ├── import_csv_to_sqlite.py         # Import CSV to database
│   ├── init_db.py                      # Initialize database schema
│   ├── train_model.py                  # Train ML model
│   ├── find_duplicate_ids.py           # Find duplicate entries
│   └── shell/                          # Shell scripts
│       ├── run_http.sh                 # Start HTTP server (local dev)
│       ├── run_https.sh                # Start HTTPS server (external access)
│       ├── setup_chatgpt_mcp.sh        # Configure ChatGPT integration
│       └── setup_claude_mcp.sh         # Configure Claude Desktop integration
├── src/                                # Source code
│   └── personal_health/
│       ├── __init__.py
│       ├── core.py                     # FastAPI app with mounted MCP
│       ├── config.py                   # Configuration handling;`
│       ├── logging_config.py           # Logging configuration
│       ├── exceptions.py               # Custom exceptions
│       ├── utils.py                    # Utility functions
│       ├── py.typed                    # PEP 561 type marker
│       ├── api/                        # API module
│       │   ├── __init__.py
│       │   ├── routes.py               # HTTP endpoints
│       │   ├── schemas.py              # Pydantic models
│       │   ├── operation_ids.py        # Operation ID constants
│       │   └── analysis.py             # Analysis logic
│       ├── db/                         # Database module
│       │   ├── __init__.py
│       │   ├── manager.py              # Database manager class
│       │   └── schema.sql              # SQLite schema
│       └── ml/                         # Machine learning module
│           ├── __init__.py
│           ├── features.py             # Feature engineering for ML model
│           └── predictor.py            # Model inference
└── tests/                              # Test suite
    ├── __init__.py
    ├── conftest.py                     # Pytest fixtures
    ├── resources/                      # Test resources
    │   └── test_data.yaml
    └── unit/                           # Unit tests
        ├── __init__.py
        ├── test_analysis.py
        ├── test_mcp_integration.py
        └── test_routes.py
```

---

## 4. Database Schema

```sql
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    meal TEXT,
    alcohol TEXT,
    stress INTEGER,
    sleep_hours REAL,
    pain_level INTEGER,
    notes TEXT
);
```

## 5. Getting Started

### Installation

```bash
# Clone and navigate to the repo
cd personal-health-mcp-system

# Use uv to sync dependencies
uv sync
```

### Database Setup

Initialize the SQLite database:

```bash
uv run init-db
```

This creates `data/health.db` with the schema above.

### Run the Server

For information about all available scripts, see [scripts/README.md](scripts/README.md).

**HTTP (Development):**

```bash
scripts/shell/run_http.sh
```

**HTTPS (External Access):**

```bash
scripts/shell/run_https.sh
```

The API will be available at:

- HTTP: `http://localhost:8080`
- HTTPS: `https://localhost:8443`
- OpenAPI docs: `/docs`
- MCP endpoint: `/mcp` (SSE protocol)

### Run Tests

```bash
uv run pytest tests/ -v
```

### Code Quality

Pre-commit hooks run automatically on commit:

```bash
uv run pre-commit run --all-files
```

---

## 6. MCP Integration

### Overview

The system exposes a **Model Context Protocol (MCP)** endpoint at `/mcp` for AI agent integration. The MCP layer wraps REST endpoints with JSON-RPC 2.0 compatible discovery and invocation.

### Quick Start with ChatGPT

1. **Start HTTPS server:**

   ```bash
   ./scripts/run_https.sh
   ```

2. **Expose via ngrok:**

   ```bash
   ngrok http https://localhost:8443
   ```

3. **Configure ChatGPT:**
   - With a Plus subscription or higher, go to chat.openai.com
   - Go to Settings → Apps & Connectors and select Create
   - Complete the form action with ngrok HTTPS URL

4. **Use natural language:**
   - "Add a health entry for today: pizza, 2 beers, stress 4, sleep 7.5 hours"
   - "Show my health entries from the last week"
   - "Summarize my health data for the past 7 days"

### Idempotency

Duplicate entries with identical values across **all fields** (date, meal, alcohol, stress, sleep_hours, pain_level, notes) are deduplicated:

- Same field values → same `entry_id` (deterministic hash)
- No duplicate database rows created
- Always returns 200 OK with existing ID

**To update context:** Use the `update_entry` operation to modify specific fields (e.g., notes, pain_level) without creating a new entry.

### Documentation

- **OpenAPI/Swagger UI:** Visit `http://localhost:8080/docs` when server is running for complete API documentation with schemas and examples
- **ReDoc:** Alternative docs at `http://localhost:8080/redoc`

---

## 7. Model Pipeline

1. Feature Engineering:

    - Convert categorical text (meal, alcohol) to binary features.
    - Add lag features (previous-day alcohol, rolling stress avg).
    - Calculate aggregate statistics.

1. Training:

    ```bash
    uv run train-model --db data/health.db
    ```

    - Output: model.pkl

1. Prediction Service:

    - Load model on server startup.
    - `predict_next_day` calls `predictor.py`

### Model Selection

A Random Forest Regressor is chosen for the pain prediction model due to its robustness, ability to handle non-linear relationships, resistance to overfitting, and handling missing data.
Health data rarely follows linear patterns, so this model helps capture complex interactions between features like meal, alcohol, stress, sleep hours, and pain levels.
Additionally, numerical features do not need to be scaled for Random Forests, and the model can provide feature importance insights, which is valuable for understanding which factors most influence pain levels.

### Feature Engineering

The following features are engineered for the pain prediction model:

- **Lag Features:** Lookback window uses previous 7 days of stress, sleep hours, and pain levels (e.g., `stress_d7`, `sleep_d7`, `pain_d7`).
  - These capture temporal patterns and trends in the data, allowing the model to learn from recent history.
  - Zero padding allows for some missing entries with a minimum of 3 days required to generate lag features.
  - For example, if a user had high stress levels for the past week, or poor sleep hours, the model may learn to associate those patterns with higher pain levels the next day.
- **Day of Week Encoding:** Categorical feature representing the day of the week (e.g., Monday, Tuesday) to capture weekly patterns in health data.
  - For example, stress levels might be higher on weekdays compared to weekends, or sleep patterns might differ based on the day of the week.
- **Aggregate Stats:** Average/max stress, sleep and pain levels over the past week to capture overall trends.
  - These features summarize the user's recent health status and can help the model identify overall patterns that may influence pain levels.

### Metrics Used

The following metrics are used to evaluate the performance of the pain prediction model:

- **Mean Absolute Error (MAE):**
  - Measures average prediction error in original units (pain points)
  - Example: MAE of 1.5 means predictions are off by ±1.5 pain points on average
  - Why: Intuitive interpretation for health context
- **Root Mean Squared Error (RMSE):**
  - Penalizes larger errors more than MAE, giving insight into occasional large misses
  - Example: RMSE of 2.0 indicates variance in prediction accuracy
  - Why: Helps identify if model has occasional large misses vs. consistent small errors
- **R-squared Score (Coefficient of Determination):**
  - Measures how much variance in the pain level is explained by the model (0.0 to 1.0)
  - Example: R-squared of 0.75 means the model explains 75% of the variance in pain levels
  - Why: Indicates overall predictive power and usefulness

#### R-squared Score History

Initial training was leaving out meal and alcohol features, which resulted in a negative R-squared score. We may as well have been predicting mean pain levels.

This score was the first to indicate poor model performance and lead to realizing that key lifestyle factors (meal and alcohol) were missing from the model. After including these features < ... to be continued ...>.

### Expanded Learning Techniques

Currently, this project is primarily intended to provide learning through doing rather than achieving a production-ready model or realistic predictions on a real dataset. The initial model was trained on a small, partially curated dataset that does not represent the complexity or size of real-world data. As is, the model may not generalize well to real-world data.

Future work to enhance should include expanding the dataset, expanding the feature set to include vectors for meal types, type of alcohol, other substance types, other lifestyle factors, food ingredients and known allergens.
Categorizing meals and alcohol into more granular types (e.g., spicy food, red wine) may help identify pain trigger patterns.
Interactions between features may be important too - such as stress x sleep interactions, or meal x alcohol interactions.

#### Different Model Types

Given the simple and small dataset, a linear regression model may be a better fit for the initial version of the project.

### Expanded Scoring Techniques

In addition to the standard regression metrics (MAE, RMSE, R-squared), additional scoring techniques should be implemented for a better evaluation of the performance as additional features are introduced and the model is trained on a larger dataset. These may include:

- **Train vs Test**
  - Useful to understand if more data is needed to avoid overfitting.
  - Why: A large gap indicates overfitting.
- **Mean Absolute Percentage Error (MAPE):**
  - Measures prediction error as a percentage of actual values
  - Example: MAPE of 20% means predictions are off by 20% on average
  - Why: Useful for understanding relative error in health context, especially when pain levels can vary widely between individuals. A 1-point error may be more significant
- **Median Absolute Error (MedAE):**
  - Measures the median of absolute errors, providing insight into a typical error un-skewed by outliers.
  - Example: If MAE=0.83 but MedAE=0.5, there are some large misses.
  - Why: More robust than MAE alone. In health data, outliers can occur due to unusual events (e.g., a particularly stressful day or a night of poor sleep), and MedAE can provide a more representative measure of typical model performance.
- **Maximum Error:**
  - Measures the largest single error in predictions.
  - Example: A maximum error of 5 means that at least one prediction was off by 5 pain points.
  - Why: Identifies worst-case scenarios, which could spot misses in an otherwise well-performing model. In health contexts, large errors could indicate critical mis-predictions that may need further investigation or model refinement.
- **Binning** the pain levels into categories (e.g., low, medium, high) and evaluating classification metrics (accuracy, precision, recall) for these bins could provide additional insights into how well the model is performing in predicting clinically relevant thresholds of pain.

---

## 8. Example Workflow

```bash
# Add new entry
curl -X POST localhost:8080/add_entry \
     -H "Content-Type: application/json" \
     -d '{"meal":"tacos","alcohol":"beer","stress":4,"pain_level":6,"notes":"felt bloated"}'

# Get week summary
curl localhost:8080/summarize_recent?window_days=7

# Run next-day prediction
curl localhost:8080/predict_next_day?date=2025-10-24
```

---

## 9. Optional Integrations

• Apple Health / Fitbit: REST or CSV import for sleep, steps, HR.
• Email/Slack Summary: Daily or weekly health report via webhook.
• MLflow or DVC: Model version tracking and experiment logging.

---

## 10. Next Steps

See the [phases.md](docs/phases.md) for detailed next steps.

1. [x] Scaffold FastAPI project with the schema above.
2. [x] Implement /add_entry and /get_entries.
3. [ ] Build training notebook (notebooks/eda.ipynb) for correlation visualization.
4. [x] Train baseline logistic regression model.
5. [x] Add /predict_next_day endpoint.
6. [x] Extend to MCP-compatible spec (JSON schema for callable functions).
