"""
PydanticAI agent with MCP tools from Cavepedia server.
"""

import os
import logging
import httpx

from pydantic_ai import Agent, ModelMessage, RunContext
from pydantic_ai.settings import ModelSettings

# Set up logging based on environment
log_level = logging.DEBUG if os.getenv("DEBUG") else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

CAVE_MCP_URL = os.getenv("CAVE_MCP_URL", "https://mcp.caving.dev/mcp")

logger.info("Initializing Cavepedia agent...")


def limit_history(ctx: RunContext[None], messages: list[ModelMessage]) -> list[ModelMessage]:
    """Limit conversation history to manage token usage and request size."""
    # Keep only the last few messages to avoid large requests hitting Cloudflare limits
    return messages[-4:]

def check_mcp_available(url: str, timeout: float = 5.0) -> bool:
    """Check if MCP server is reachable via health endpoint."""
    try:
        # Use the health endpoint instead of the MCP endpoint
        health_url = url.rsplit("/", 1)[0] + "/health"
        response = httpx.get(health_url, timeout=timeout, follow_redirects=True)
        if response.status_code == 200:
            return True
        logger.warning(f"MCP health check returned {response.status_code}")
        return False
    except Exception as e:
        logger.warning(f"MCP server not reachable: {e}")
        return False

# Check if MCP is available at startup
MCP_AVAILABLE = check_mcp_available(CAVE_MCP_URL)
logger.info(f"MCP server available: {MCP_AVAILABLE}")

AGENT_INSTRUCTIONS = """Caving assistant. Help with exploration, safety, surveying, locations, geology, equipment, history, conservation.

Rules:
1. Cite sources when possible.
2. Say when uncertain. Never hallucinate.
3. Be safety-conscious.
4. Can create ascii diagrams/maps.
5. Be direct—no sycophantic phrases.
6. Keep responses concise.
7. Use tools sparingly—one search usually suffices. Answer from your knowledge when possible."""


def create_agent(user_roles: list[str] | None = None):
    """Create an agent with MCP tools configured for the given user roles."""
    toolsets = []

    if MCP_AVAILABLE and user_roles:
        try:
            import json
            from pydantic_ai.mcp import MCPServerStreamableHTTP

            roles_header = json.dumps(user_roles)
            logger.info(f"Creating MCP server with roles: {roles_header}")

            mcp_server = MCPServerStreamableHTTP(
                url=CAVE_MCP_URL,
                headers={"x-user-roles": roles_header},
                timeout=30.0,
            )
            toolsets.append(mcp_server)
            logger.info(f"MCP server configured with roles: {user_roles}")
        except Exception as e:
            logger.warning(f"Could not configure MCP server: {e}")
    elif not user_roles:
        logger.info("No user roles provided - MCP tools disabled")
    else:
        logger.info("MCP server unavailable - running without MCP tools")

    return Agent(
        model="anthropic:claude-sonnet-4-5",
        toolsets=toolsets if toolsets else None,
        instructions=AGENT_INSTRUCTIONS,
        history_processors=[limit_history],
        model_settings=ModelSettings(max_tokens=4096),
    )


# Create a default agent for health checks etc
agent = create_agent()

logger.info("Agent module initialized successfully")
