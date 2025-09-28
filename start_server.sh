#!/usr/bin/env bash
"""
Production startup script for Render deployment.
"""

# Set environment variables with defaults
export HOST=${HOST:-"0.0.0.0"}
export PORT=${PORT:-8000}
export WORKERS=${WORKERS:-2}

echo "Starting ETF Builder API on $HOST:$PORT with $WORKERS workers"

# Check if required files exist
if [ ! -f "etf_data.sqlite" ]; then
    echo "Error: etf_data.sqlite not found in current directory"
    exit 1
fi

if [ ! -f "data/etfs.json" ]; then
    echo "Error: data/etfs.json not found"
    exit 1
fi

# Start the server
exec uvicorn src.builder.main:app \
    --host $HOST \
    --port $PORT \
    --workers $WORKERS \
    --log-level info \
    --access-log