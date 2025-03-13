#!/bin/bash
# Install script for SessionMCP

set -e

echo "Installing SessionMCP..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing..."
    # Install uv using the official installer
    curl -sSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for this session
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Create a virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Install the package
echo "Installing the package..."
uv pip install -e .

echo ""
echo "Installation complete! You can now use the following commands:"
echo "  sessionmcp        - Run the standard SessionMCP proxy"
echo "  smcp              - Shorthand alias for sessionmcp"
echo "  sessionmcp-enhanced - Run SessionMCP with enhanced session parameter support"
echo ""
echo "Example usage:"
echo "  sessionmcp --sse-port 8080 -- python -m mcp.client.stdio"
echo "  sessionmcp-enhanced --sse-port 8080 -- python -m mcp.client.stdio"
echo ""
echo "Then in Cursor, use this URL to connect with session parameters:"
echo "  http://localhost:8080/sse?auth=YOUR_API_KEY&client_id=YOUR_CLIENT_ID" 