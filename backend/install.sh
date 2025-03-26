#!/bin/bash
# Activate the virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run the server
python -m uvicorn main:app --reload --port 8000 