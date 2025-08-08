#!/bin/bash
set -e

echo "=== rhino-mcp Install/Update Script ==="

# Parse arguments
DEV_MODE=false
if [[ "$1" == "--dev" ]]; then
    DEV_MODE=true
    echo "[MODE] Development mode (install/update only, do not start MCP Server)"
fi

# 1. Check if uv is installed
if ! command -v uv &> /dev/null
then
    echo "[INFO] uv not found. Installing via Homebrew..."
    brew install uv
fi

# 2. Clone or update repository
if [ ! -d "rhino-mcp" ]; then
    echo "[STEP] Cloning t60011/rhino-mcp..."
    git clone https://github.com/t60011/rhino-mcp.git
else
    echo "[STEP] Updating t60011/rhino-mcp..."
    cd rhino-mcp
    git pull
    cd ..
fi

# 3. Go to the directory containing pyproject.toml
cd rhino-mcp/rhino_mcp

# 4. Create and activate virtual environment
if [ ! -d ".venv" ]; then
    echo "[STEP] Creating Python virtual environment..."
    uv venv
fi
source .venv/bin/activate

# 5. Install or update package
echo "[STEP] Installing/Updating rhinomcp..."
uv pip install -e .

# 6. Start MCP Server unless in dev mode
if [ "$DEV_MODE" = false ]; then
    echo "[STEP] Starting rhinomcp MCP Server..."
    rhinomcp
else
    echo "[DONE] Installation/Update complete (development mode, server not started)"
fi
