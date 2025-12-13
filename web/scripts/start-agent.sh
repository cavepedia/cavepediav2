#!/bin/bash

# Navigate to the agent directory
cd "$(dirname "$0")/../agent" || exit 1

# Run the agent in production mode
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000 --workers 2
