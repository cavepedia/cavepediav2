"""
Self-hosted PydanticAI agent server using AG-UI protocol.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv
from pydantic_ai.usage import UsageLimits
from pydantic_ai.settings import ModelSettings

# Load environment variables BEFORE importing agent
load_dotenv()

# Set up logging based on environment
from pythonjsonlogger import jsonlogger

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
json_formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")

# Configure root logger with JSON
handler = logging.StreamHandler()
handler.setFormatter(json_formatter)
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    handlers=[handler],
)
logger = logging.getLogger(__name__)

# Apply JSON formatter to uvicorn loggers (works even when run via `uvicorn src.main:app`)
for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    uvicorn_logger = logging.getLogger(uvicorn_logger_name)
    uvicorn_logger.handlers = [handler]
    uvicorn_logger.setLevel(getattr(logging, log_level, logging.INFO))
    uvicorn_logger.propagate = False

# Validate required environment variables
if not os.getenv("ANTHROPIC_API_KEY"):
    logger.error("ANTHROPIC_API_KEY environment variable is required")
    sys.exit(1)

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.routing import Route

from pydantic_ai.ui.ag_ui import AGUIAdapter

from src.agent import create_agent

logger.info("Creating AG-UI app...")


async def handle_agent_request(request: Request) -> Response:
    """Handle incoming AG-UI requests with dynamic role-based MCP configuration."""

    # Extract user roles from request headers
    roles_header = request.headers.get("x-user-roles", "")
    user_roles = []

    if roles_header:
        try:
            user_roles = json.loads(roles_header)
            logger.info(f"Request received with roles: {user_roles}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse x-user-roles header: {e}")

    # Extract sources-only mode from header
    sources_only = request.headers.get("x-sources-only", "false") == "true"
    if sources_only:
        logger.info("Sources-only mode enabled")

    # Create agent with the user's roles and mode
    agent = create_agent(user_roles, sources_only=sources_only)

    # Dispatch the request - tool limits handled by ToolCallLimiter in agent.py
    return await AGUIAdapter.dispatch_request(
        request,
        agent=agent,
        usage_limits=UsageLimits(
            request_limit=10,     # Safety net for runaway requests
        ),
        model_settings=ModelSettings(max_tokens=4096),
    )


async def health(request: Request) -> Response:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


app = Starlette(
    routes=[
        Route("/", handle_agent_request, methods=["POST"]),
        Route("/health", health, methods=["GET"]),
    ],
)

logger.info("AG-UI app created successfully")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port)
