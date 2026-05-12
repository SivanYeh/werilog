#!/bin/bash

# Exit on error
set -e

echo "🚀 Initializing environment with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first (e.g., 'curl -LsSf https://astral.sh/uv/install.sh | sh')"
    exit 1
fi

# Initialize project if pyproject.toml is missing
if [ ! -f "pyproject.toml" ]; then
    echo "📄 Creating pyproject.toml..."
    uv init --app
else
    echo "✨ pyproject.toml already exists."
fi

# Install/Update dependencies and generate uv.lock
echo "📥 Adding and syncing dependencies..."
# Use 'uv add' to ensure they are in pyproject.toml
uv add tkinter re

# Synchronize the environment (this creates/updates uv.lock)
echo "🔄 Synchronizing environment..."
uv sync

echo "✅ Environment setup complete!"
echo "Files created/updated: pyproject.toml, uv.lock"
echo "To run your script, use: uv run python src/run_mine.py"
