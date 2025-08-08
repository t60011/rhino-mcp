#!/bin/bash
set -e

echo "=== rhino-mcp Install/Update Script ==="

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

echo "[DONE] Installation/Update complete."
echo "[INFO] To start MCP server, run rhino_mcp_client.py inside Rhino."
