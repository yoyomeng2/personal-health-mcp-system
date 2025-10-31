#!/bin/bash
# Setup script to configure Personal Health MCP for ChatGPT
# Currently, you need a ChatGPC license ABOVE Plus to use MCPs

set -e

# ChatGPT MCP config location (macOS)
CONFIG_DIR="$HOME/Library/Application Support/ChatGPT/mcp_config"
CONFIG_FILE="$CONFIG_DIR/personal_health.json"

echo "Setting up Personal Health MCP for ChatGPT..."

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Create the MCP configuration
cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "personal-health": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "name": "Personal Health MCP",
      "description": "Track and analyze personal health data including meals, sleep, stress, and pain levels"
    }
  }
}
EOF

echo "✓ Configuration created at: $CONFIG_FILE"
echo ""
echo "Next steps:"
echo "1. Make sure your server is running:"
echo "   cd $PROJECT_ROOT"
echo "   uv run uvicorn personal_health.core:app --host 0.0.0.0 --port 8080"
echo ""
echo "2. Restart ChatGPT desktop app"
echo ""
echo "3. In ChatGPT, you should see 'Personal Health MCP' available"
echo "   The following tools will be available:"
echo "   - add_entry: Add a new health entry"
echo "   - get_entries: Get recent health entries"
echo "   - get_summary: Get summary of recent health data"
echo ""
echo "4. Test it by asking ChatGPT:"
echo "   'Add a health entry for today with 7 hours of sleep and stress level 3'"
