#!/bin/bash
# Run Personal Health MCP server with HTTPS support

set -e

# Project root (go up 2 levels from scripts/shell/ to reach repo root)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Certificate files
CERT_FILE="$PROJECT_ROOT/cert.pem"
KEY_FILE="$PROJECT_ROOT/key.pem"
TEMP_CERT=false

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down server..."
    if [ "$TEMP_CERT" = true ]; then
        echo "Removing temporary certificates..."
        rm -f "$CERT_FILE" "$KEY_FILE"
        echo "✓ Certificates removed"
    fi
}

# Register cleanup on exit
trap cleanup EXIT INT TERM

# Generate self-signed certificate if it doesn't exist
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "Generating temporary self-signed SSL certificate..."
    openssl req -x509 -newkey rsa:4096 -nodes \
        -out "$CERT_FILE" \
        -keyout "$KEY_FILE" \
        -days 365 \
        -subj "/CN=localhost" \
        -quiet
    TEMP_CERT=true
    echo "✓ Certificate generated (will be removed on exit)"
fi

# Default port
PORT="${PORT:-8443}"

echo "Starting Personal Health MCP server with HTTPS..."
echo "Server will be available at: https://localhost:$PORT"
echo ""
echo "Note: Using self-signed certificate. For ChatGPT/external access:"
echo "  1. Use ngrok: ngrok http https://localhost:$PORT"
echo "  2. Update ChatGPT config with ngrok URL"
echo ""
echo "Press Ctrl+C to stop server"
echo ""

# Start server
uv run uvicorn personal_health.core:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --ssl-keyfile="$KEY_FILE" \
    --ssl-certfile="$CERT_FILE" \
    --reload
