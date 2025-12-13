#!/bin/bash

# Navigate to the agent directory
cd "$(dirname "$0")/../agent" || exit 1

# Run the agent using uvicorn with reload for development
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
