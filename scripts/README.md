# Scripts

Utility scripts for managing the Personal Health MCP System.

## Structure

```text
scripts/
├── __init__.py                    # Python package marker
├── export_sqlite_to_csv.py        # Export database entries to CSV format
├── generate_sample_csv.py         # Generate sample health data CSV for testing
├── import_csv_to_sqlite.py        # Import CSV data into the database
├── init_db.py                     # Initialize the database schema
├── train_model.py                 # Train the pain prediction ML model
└── shell/                         # Shell scripts for server management
    ├── run_http.sh                # Start MCP server with HTTP (local dev)
    ├── run_https.sh               # Start MCP server with HTTPS (external access)
    ├── setup_chatgpt_mcp.sh       # Configure ChatGPT MCP integration
    └── setup_claude_mcp.sh        # Configure Claude Desktop MCP integration
```

## Python Scripts

### Database Management

- **`init_db.py`** - Initialize or recreate the SQLite database schema
- **`export_sqlite_to_csv.py`** - Export all health entries to a CSV file for backup or analysis
- **`import_csv_to_sqlite.py`** - Import health entries from CSV, with deduplication via deterministic ID generation

### Data Generation & Testing

- **`generate_sample_csv.py`** - Generate synthetic health data CSV for testing and development

### Machine Learning

- **`train_model.py`** - Train the pain prediction model using historical data
  - Trains Random Forest regressor
  - Generates feature importance plots and saves model to `models/` directory

## Shell Scripts

### Server Management

- **`shell/run_http.sh`** - Start the MCP server with HTTP on port 8080
  - **Use for**: Local development, local agent MCP integration

- **`shell/run_https.sh`** - Start the MCP server with HTTPS on port 8443
  - **Use for**: External access (ChatGPT, ngrok tunneling)
  - **Note**: Pair with ngrok for valid HTTPS certificate when exposing externally

### MCP Client Setup

- **`shell/setup_chatgpt_mcp.sh`** - Configure ChatGPT custom actions to use the MCP server
- **`shell/setup_claude_mcp.sh`** - Configure Claude Desktop MCP integration
