#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Project root is two levels up from scripts/linux/
ROOT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment (.venv) not found. Please run scripts/linux/install.sh first."
    exit 1
fi

source .venv/bin/activate
export HF_HUB_DISABLE_PROGRESS_BARS=1
echo "🎨 Launching wildcards-gen GUI..."
python -m wildcards_gen.cli gui
