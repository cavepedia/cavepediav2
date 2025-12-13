"""
PydanticAI agent with MCP tools from Cavepedia server.
"""

import os
import logging
import httpx

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel

# Set up logging based on environment
log_level = logging.DEBUG if os.getenv("DEBUG") else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

CAVE_MCP_URL = os.getenv("CAVE_MCP_URL", "https://mcp.caving.dev/mcp")

logger.info("Initializing Cavepedia agent...")

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

# Try to configure MCP if server is available
toolsets = []
if check_mcp_available(CAVE_MCP_URL):
    try:
        from pydantic_ai.mcp import MCPServerStreamableHTTP
        mcp_server = MCPServerStreamableHTTP(
            url=CAVE_MCP_URL,
            timeout=30.0,
        )
        toolsets.append(mcp_server)
        logger.info(f"MCP server configured: {CAVE_MCP_URL}")
    except Exception as e:
        logger.warning(f"Could not configure MCP server: {e}")
else:
    logger.info("MCP server unavailable - running without MCP tools")

# Create the agent with Google Gemini model
agent = Agent(
    model=GoogleModel("gemini-3-pro-preview"),
    toolsets=toolsets if toolsets else None,
    instructions="""You are a helpful caving assistant. Help users with all aspects of caving including cave exploration, safety, surveying techniques, cave locations, geology, equipment, history, conservation, and any other caving-related topics.

IMPORTANT RULES:
1. Always cite your sources at the end of each response when possible.
2. If you're not certain about information, say so clearly. Do NOT make up information or hallucinate facts.
3. Provide accurate, helpful, and safety-conscious information.""",
)

logger.info(f"Agent initialized successfully (MCP: {'enabled' if toolsets else 'disabled'})")
