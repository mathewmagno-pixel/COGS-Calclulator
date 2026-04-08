#!/bin/bash
# ============================================================
# J.A.R.V.I.S. — Setup Script
# ============================================================
# This script creates a virtual environment, installs
# dependencies, and prepares JARVIS for first run.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║     J.A.R.V.I.S. — Setup Wizard         ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# 1. Check Python
echo "  [1/4] Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "  ERROR: Python 3.10+ is required but not found."
    echo "  Install Python from https://python.org"
    exit 1
fi

PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Found Python $PY_VERSION"

# 2. Create virtual environment
echo "  [2/4] Creating virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo "  Created venv/"
else
    echo "  venv/ already exists, skipping"
fi

# Activate venv
source venv/bin/activate

# 3. Install dependencies
echo "  [3/4] Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  All packages installed"

# 4. Create .env if needed
echo "  [4/4] Checking configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  Created .env from template"
    echo ""
    echo "  ⚠  IMPORTANT: Edit jarvis/.env with your API keys"
    echo "     At minimum, you need: ANTHROPIC_API_KEY"
    echo ""
else
    echo "  .env already exists"
fi

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║           Setup Complete!                ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
echo "  To start JARVIS:"
echo ""
echo "    cd jarvis"
echo "    source venv/bin/activate"
echo "    python main.py"
echo ""
echo "  JARVIS will open in your browser at http://127.0.0.1:8550"
echo ""
