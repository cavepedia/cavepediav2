# syntax=docker/dockerfile:1

FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY main.py server.py ./

EXPOSE 8000

CMD ["uv", "run", "python", "server.py"]
