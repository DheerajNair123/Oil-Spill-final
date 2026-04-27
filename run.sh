#!/bin/bash
# Oil Spill Detection API - Startup Script

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/Scripts/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the API server
echo "Starting Oil Spill Detection API..."
uvicorn oil_spill:app --reload --host 0.0.0.0 --port 8000
