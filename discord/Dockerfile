FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create non-root user early
RUN useradd --create-home --shell /bin/bash discorduser

WORKDIR /app
RUN chown discorduser:discorduser /app

ENV PYTHONPATH=/app

# Copy dependency files and set ownership
COPY --chown=discorduser:discorduser pyproject.toml uv.lock ./

# Switch to non-root user before installing dependencies
USER discorduser

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY --chown=discorduser:discorduser src ./src

CMD ["uv", "run", "--frozen", "python", "-m", "src.main"]
