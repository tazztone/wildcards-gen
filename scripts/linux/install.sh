#!/bin/bash

# wildcards-gen Installation Script (Linux/macOS)
# This script should be run from the repository root or its own directory.

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Project root is two levels up from scripts/linux/
ROOT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

cd "$ROOT_DIR"

# Exit on error
set -e

echo "🚀 Starting installation of wildcards-gen..."

# Check if uv is installed (recommended)
if command -v uv &> /dev/null
then
    echo "✨ uv found! Using uv for faster installation."
    uv venv .venv
    source .venv/bin/activate
    uv pip install -e .
else
    echo "🐍 uv not found. Falling back to standard venv/pip."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -e .
fi

echo ""
echo "✅ Installation complete!"
echo "-----------------------------------------------"
echo "To use wildcards-gen, always activate your venv first:"
echo "source .venv/bin/activate"
echo ""
echo "Then you can run commands like:"
echo "wildcards-gen --help"
echo "wildcards-gen gui"
echo "-----------------------------------------------"
