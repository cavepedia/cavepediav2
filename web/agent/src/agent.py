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

from typing import Any
from pydantic_ai import Agent, ModelMessage, RunContext
from pydantic_ai.settings import ModelSettings
from pydantic_ai.mcp import CallToolFunc

CAVE_MCP_URL = os.getenv("CAVE_MCP_URL", "https://mcp.caving.dev/mcp")

logger.info(f"Initializing Cavepedia agent with CAVE_MCP_URL={CAVE_MCP_URL}")


def limit_history(ctx: RunContext[None], messages: list[ModelMessage]) -> list[ModelMessage]:
    """Limit history and clean up orphaned tool calls to prevent API errors."""
    from pydantic_ai.messages import ModelResponse, ToolCallPart

    if not messages:
        return messages

    # Keep only the last 4 messages
    messages = messages[-4:]

    # Check if the last message is an assistant response with a tool call
    # If so, remove it - it's orphaned (no tool result followed)
    if messages:
        last_msg = messages[-1]
        if isinstance(last_msg, ModelResponse):
            has_tool_call = any(isinstance(part, ToolCallPart) for part in last_msg.parts)
            if has_tool_call:
                logger.warning("Removing orphaned tool call from history")
                return messages[:-1]

    return messages

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
3. Be safety-conscious.
4. Can create ascii diagrams/maps.
5. Be direct—no sycophantic phrases.
6. Keep responses concise.
7. Use tools sparingly—one search usually suffices.
8. If you hit the search limit, end your reply with an italicized note: *Your question may be too broad. Try asking something more specific.* Do NOT mention "tools" or "tool limits"—the user doesn't know what those are."""

SOURCES_ONLY_INSTRUCTIONS = """SOURCES ONLY MODE: Give a 1-2 sentence summary maximum. Focus on listing sources in a bulleted list. No detailed explanations."""


def create_tool_call_limiter(max_calls: int = 3):
    """Create a process_tool_call callback that limits tool calls."""
    call_count = [0]  # Mutable container for closure

    async def process_tool_call(
        ctx: RunContext,
        call_tool: CallToolFunc,
        name: str,
        tool_args: dict[str, Any],
    ):
        call_count[0] += 1
        if call_count[0] > max_calls:
            return (
                f"SEARCH LIMIT REACHED: You have made {max_calls} searches. "
                "Stop searching and answer now with what you have. "
                "End your reply with: *Your question may be too broad. Try asking something more specific.*"
            )
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
                headers={"x-user-roles": roles_header},
                timeout=30.0,
                process_tool_call=create_tool_call_limiter(max_calls=3),
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
        history_processors=[limit_history],
        model_settings=ModelSettings(max_tokens=4096),
    )


logger.info("Agent module initialized successfully")
