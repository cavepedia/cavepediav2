"""
PydanticAI agent with MCP tools from Cavepedia server.
"""

import os
import logging
import httpx
import logfire

# Set up logging BEFORE logfire (otherwise basicConfig is ignored)
from pythonjsonlogger import jsonlogger

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    handlers=[handler],
)
logger = logging.getLogger(__name__)

# Configure Logfire for observability
logfire.configure(
    environment=os.getenv('ENVIRONMENT', 'development'),
)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx()

from pydantic_ai import Agent, RunContext
from pydantic_ai.settings import ModelSettings
from pydantic_ai.mcp import CallToolFunc

CAVE_MCP_URL = os.getenv("CAVE_MCP_URL", "https://mcp.caving.dev/mcp")

logger.info(f"Initializing Cavepedia agent with CAVE_MCP_URL={CAVE_MCP_URL}")


def check_mcp_available(url: str, timeout: float = 5.0) -> bool:
    """Check if MCP server is reachable via health endpoint."""
    try:
        # Use the health endpoint instead of the MCP endpoint
        health_url = url.rsplit("/", 1)[0] + "/health"
        logger.info(f"Checking MCP health at: {health_url}")
        response = httpx.get(health_url, timeout=timeout, follow_redirects=True)
        if response.status_code == 200:
            return True
        logger.warning(f"MCP health check returned {response.status_code}")
        return False
    except Exception as e:
        logger.warning(f"MCP server not reachable: {e}")
        return False

# MCP availability is checked lazily in create_agent()

AGENT_INSTRUCTIONS = """Caving assistant. Help with exploration, safety, surveying, locations, geology, equipment, history, conservation.

Rules:
1. ALWAYS cite sources in a bulleted list at the end of every reply, even if there's only one. Format them human-readably (e.g., "- The Trog 2021, page 19" not "vpi/trog/2021-trog.pdf/page-19.pdf").
2. Say when uncertain. Never hallucinate.
3. Be direct—no sycophantic phrases.
4. Keep responses concise.
5. SEARCH EXACTLY ONCE. After searching, IMMEDIATELY answer using those results. NEVER search again - additional searches are blocked and waste resources.
6. For rescue, accident, or emergency-related queries, use priority_prefixes=['nss/aca'] when searching to prioritize official accident reports."""

SOURCES_ONLY_INSTRUCTIONS = """SOURCES ONLY MODE: Give exactly ONE sentence summary. Then list sources with specific page numbers (e.g., "- The Trog 2021, page 19"). No explanations."""


def create_search_limiter():
    """Block searches after the first one."""
    searched = [False]

    async def process_tool_call(
        ctx: RunContext,
        call_tool: CallToolFunc,
        name: str,
        tool_args: dict,
    ):
        if name == "search_caving_documents":
            if searched[0]:
                return "You have already searched. Use the results you have."
            searched[0] = True
        return await call_tool(name, tool_args)

    return process_tool_call


def create_agent(user_roles: list[str] | None = None, sources_only: bool = False):
    """Create an agent with MCP tools configured for the given user roles."""
    toolsets = []

    # Check MCP availability lazily (each request) to handle startup race conditions
    mcp_available = check_mcp_available(CAVE_MCP_URL) if user_roles else False

    if mcp_available and user_roles:
        try:
            import json
            from pydantic_ai.mcp import MCPServerStreamableHTTP

            roles_header = json.dumps(user_roles)
            logger.info(f"Creating MCP server with roles: {roles_header}")

            mcp_server = MCPServerStreamableHTTP(
                url=CAVE_MCP_URL,
                headers={
                    "x-user-roles": roles_header,
                    "x-sources-only": "true" if sources_only else "false",
                },
                timeout=30.0,
                process_tool_call=create_search_limiter(),
            )
            toolsets.append(mcp_server)
            logger.info(f"MCP server configured with roles: {user_roles}")
        except Exception as e:
            logger.warning(f"Could not configure MCP server: {e}")
    elif not user_roles:
        logger.info("No user roles provided - MCP tools disabled")
    else:
        logger.info("MCP server unavailable - running without MCP tools")

    # Build instructions based on mode
    instructions = AGENT_INSTRUCTIONS
    if sources_only:
        instructions = f"{SOURCES_ONLY_INSTRUCTIONS}\n\n{AGENT_INSTRUCTIONS}"

    return Agent(
        model="anthropic:claude-sonnet-4-5",
        toolsets=toolsets if toolsets else None,
        instructions=instructions,
        model_settings=ModelSettings(max_tokens=4096),
    )


logger.info("Agent module initialized successfully")
