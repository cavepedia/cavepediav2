"""
PydanticAI agent with MCP tools from Cavepedia server.
"""

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.mcp import MCPServerStreamableHTTP


# Create MCP server connection to Cavepedia
mcp_server = MCPServerStreamableHTTP(
    url="https://mcp.caving.dev/mcp",
    timeout=30.0,
)

# Create the agent with Google Gemini model
agent = Agent(
    model=GoogleModel("gemini-2.5-pro"),
    toolsets=[mcp_server],
    instructions="""You are a helpful assistant with access to cave-related information through the Cavepedia MCP server. You can help users find information about caves, caving techniques, and related topics.

IMPORTANT RULES:
1. Always cite your sources at the end of each response. List the specific sources/documents you used.
2. If you cannot find information on a topic, say so clearly. Do NOT make up information or hallucinate facts.
3. If the MCP tools return no results, acknowledge that you couldn't find the information rather than guessing.""",
)
