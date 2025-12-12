# syntax=docker/dockerfile:1

FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY main.py langgraph.json ./

# LangGraph API server port
EXPOSE 8000

# Run LangGraph server
CMD ["uv", "run", "langgraph", "up", "--host", "0.0.0.0", "--port", "8000"]
