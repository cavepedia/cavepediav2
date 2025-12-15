"""
Self-hosted PydanticAI agent server using AG-UI protocol.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Load environment variables BEFORE importing agent
load_dotenv()

# Set up logging based on environment
log_level = logging.DEBUG if os.getenv("DEBUG") else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Validate required environment variables (either API key or service account)
if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    logger.error("Either GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS is required")
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
    # Debug: log all incoming headers
    logger.info(f"DEBUG: All request headers: {dict(request.headers)}")

    # Extract user roles from request headers
    roles_header = request.headers.get("x-user-roles", "")
    logger.info(f"DEBUG: x-user-roles header value: '{roles_header}'")
    user_roles = []

    if roles_header:
        try:
            user_roles = json.loads(roles_header)
            logger.info(f"Request received with roles: {user_roles}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse x-user-roles header: {e}")

    # Create agent with the user's roles
    agent = create_agent(user_roles)

    # Dispatch the request using AGUIAdapter
    return await AGUIAdapter.dispatch_request(request, agent=agent)


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
