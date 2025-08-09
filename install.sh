#!/bin/bash
set -euo pipefail

echo "=== rhino-mcp Install/Update Script ==="

# 0) Helpers
exists_cmd() { command -v "$1" >/dev/null 2>&1; }

# 1) Ensure uv is present
if ! exists_cmd uv; then
  echo "[INFO] uv not found. Installing via Homebrew..."
  if exists_cmd brew; then
    brew install uv
  else
    echo "[ERROR] Homebrew not found. Please install Homebrew first: https://brew.sh"
    exit 1
  fi
fi

# 2) Clone or update repository (run from any directory)
if [ ! -d "rhino-mcp" ]; then
  echo "[STEP] Cloning t60011/rhino-mcp..."
  git clone https://github.com/t60011/rhino-mcp.git
else
  echo "[STEP] Updating t60011/rhino-mcp..."
  ( cd rhino-mcp && git pull --ff-only )
fi

# 3) Enter subdir that contains pyproject.toml
cd rhino-mcp/rhino_mcp

# 4) Create & activate venv
if [ ! -d ".venv" ]; then
  echo "[STEP] Creating Python virtual environment..."
  uv venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 5) Install package (editable) + dependencies
echo "[STEP] Installing package (-e .)..."
uv pip install -e .

# Prefer project-level requirements.txt if present
if [ -f "../requirements.txt" ]; then
  echo "[STEP] Installing dependencies from ../requirements.txt ..."
  uv pip install -r ../requirements.txt
elif [ -f "requirements.txt" ]; then
  echo "[STEP] Installing dependencies from requirements.txt ..."
  uv pip install -r requirements.txt
else
  echo "[INFO] No requirements.txt found. Assuming pyproject dependencies are sufficient."
fi

echo "----------------------------------------"
echo "[DONE] Install/Update complete."
echo "[INFO] Virtualenv: $(pwd)/.venv"
echo "[INFO] Python: $(python -V)"
echo "----------------------------------------"
echo "[NEXT] Start the server from Rhino (run rhino_mcp_client.py)."
