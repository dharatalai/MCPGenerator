#!/bin/bash
# Simple script to activate the Python virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Source the activate script
source "$SCRIPT_DIR/venv/bin/activate"

# Verify the environment is activated
echo "Python executable: $(which python)"
echo "Python version: $(python --version)"
echo "Virtual environment activated successfully!" 