#!/bin/bash
# Run Personal Health MCP server with HTTP (no SSL)

set -e

# Project root (go up 2 levels from scripts/shell/ to reach repo root)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Default port
PORT="${PORT:-8080}"

echo "Starting Personal Health MCP server with HTTP..."
echo "Server will be available at: http://localhost:$PORT"
echo ""
echo "Warning: This is HTTP only (no encryption)."
echo "For external/ChatGPT access, use scripts/run_https.sh instead."
echo ""
echo "Press Ctrl+C to stop server"
echo ""

# Start server
uv run uvicorn personal_health.core:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --reload
