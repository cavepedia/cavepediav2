FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV PYTHONPATH=/app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY server.py ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash mcp
USER mcp

EXPOSE 8021

ENV PORT=8021
ENV HOST="0.0.0.0"

CMD ["uv", "run", "--frozen", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8021"]
