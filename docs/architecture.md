# Personal Health MCP System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Agent[AI Agent<br/>ChatGPT/Claude]
        User[User]
    end

    subgraph "API Layer"
        MCP[MCP Server<br/>FastAPI]
        Routes[API Routes<br/>routes.py]
    end

    subgraph "Business Logic"
        FeatureExt[Feature Extraction<br/>feature_extraction.py]
        Predictor[Pain Predictor<br/>predictor.py]
        Analysis[Analysis<br/>analysis.py]
    end

    subgraph "ML/LLM Layer"
        Provider[LLM Provider<br/>OpenAI/Ollama]
        Model[Random Forest<br/>Model]
        Features[Feature Definitions<br/>features.py]
    end

    subgraph "Data Layer"
        DBManager[Database Manager<br/>manager.py]
        UserProfile[User Profile<br/>user_profile.py]
        SQLite[(SQLite DB<br/>health.db)]
    end

    User -->|Natural Language| Agent
    Agent -->|MCP Tools| MCP
    MCP --> Routes

    Routes -->|Entry Operations| DBManager
    Routes -->|Feature Extraction| FeatureExt
    Routes -->|Predictions| Predictor
    Routes -->|Analysis| Analysis

    FeatureExt -->|Get Profile| UserProfile
    FeatureExt -->|LLM Call| Provider
    FeatureExt -->|Uses| Features

    Predictor -->|Load Model| Model
    Predictor -->|Read Entries| DBManager
    Predictor -->|Uses| Features

    Analysis -->|Correlations| DBManager

    DBManager --> SQLite
    UserProfile --> SQLite

    Provider -->|Extract Features| FeatureExt

    style Agent fill:#e1f5ff
    style MCP fill:#fff4e1
    style Provider fill:#f0e1ff
    style SQLite fill:#e1ffe1
```

## Component Descriptions

### Client Layer
- **AI Agent**: External AI agents (ChatGPT, Claude) that interact via MCP protocol
- **User**: End user providing natural language input

### API Layer
- **MCP Server**: FastAPI server exposing MCP tools
- **API Routes**: RESTful endpoints for all operations

### Business Logic
- **Feature Extraction**: LLM-based extraction of binary features from meal descriptions
- **Pain Predictor**: ML-based pain level prediction using Random Forest
- **Analysis**: Correlation and trigger analysis

### ML/LLM Layer
- **LLM Provider**: OpenAI or Ollama for feature extraction
- **Random Forest Model**: Trained model for pain prediction
- **Feature Definitions**: Enums defining 19 binary features

### Data Layer
- **Database Manager**: SQLite operations and migrations
- **User Profile**: Dietary preferences and profile management
- **SQLite DB**: Persistent storage for entries and profiles

## Key Data Flows

1. **Entry Creation**: User → Agent → MCP → Routes → DBManager → SQLite
2. **Feature Extraction**: Routes → FeatureExt → Provider (LLM) → Extract → Update DB
3. **Pain Prediction**: Routes → Predictor → Load Model → Read Entries → Predict
4. **Profile Updates**: Agent → MCP → Routes → UserProfile → SQLite

## Technology Stack

- **API Framework**: FastAPI
- **Database**: SQLite with custom migration system
- **ML Framework**: scikit-learn (Random Forest)
- **LLM Providers**: OpenAI GPT-4o-mini / Ollama (local)
- **Feature Engineering**: 47 features (21 lag + 1 temporal + 6 rolling + 19 binary)
- **Protocol**: Model Context Protocol (MCP)
