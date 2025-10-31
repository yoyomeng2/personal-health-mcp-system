#!/bin/bash
# Setup script to configure Personal Health MCP for Claude Desktop

set -e

# Claude Desktop config location (macOS)
CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

echo "Setting up Personal Health MCP for Claude Desktop..."

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Backup existing config if it exists
if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✓ Existing config backed up"
fi

# Create the MCP configuration
# Note: Claude Desktop expects stdio transport with a command to run
# We use a Python proxy script that bridges stdio <-> HTTP
cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "personal-health": {
      "command": "python3",
      "args": [
        "$PROJECT_ROOT/src/project_health/mcp_stdio_proxy.py"
      ]
    }
  }
}
EOF

echo "✓ Configuration created at: $CONFIG_FILE"
echo ""
echo "Next steps:"
echo "1. Make sure your HTTPS server is running:"
echo "   cd $PROJECT_ROOT"
echo "   src/project_health/scripts/run_https.sh"
echo ""
echo "2. Restart Claude Desktop application"
echo ""
echo "3. In Claude, you should see 'personal-health' MCP server available"
echo "   The following tools will be available:"
echo "   - add_entry: Add a new health entry"
echo "   - get_entries: Get recent health entries"
echo "   - get_summary: Get summary of recent health data"
echo ""
echo "4. Test it by asking Claude:"
echo "   'Add a health entry for today with 7 hours of sleep and stress level 3'"
echo ""
echo "Note: If using ngrok, update the URL in $CONFIG_FILE to your ngrok URL"
