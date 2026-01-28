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
echo "🧠 Generating Universal Smart Skeleton (Tencent Dataset)..."
echo "This may take a moment to download metadata and process hierarchy..."

wildcards-gen dataset tencent --smart -o output/universal_skeleton.yaml

echo "✅ Done! Skeleton saved to output/universal_skeleton.yaml"
