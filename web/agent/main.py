"""
This is the main entry point for the agent.
It defines the workflow graph, state, tools, nodes and edges.
"""

from typing import Any, List, Callable, Awaitable
import json

from langchain.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, MessagesState, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest, MCPToolCallResult


class AgentState(MessagesState):
    """
    Here we define the state of the agent

    In this instance, we're inheriting from MessagesState, which will bring in
    the messages field for conversation history.
    """

    tools: List[Any]


# @tool
# def your_tool_here(your_arg: str):
#     """Your tool description here."""
#     print(f"Your tool logic here")
#     return "Your tool response here."

backend_tools = [
    # your_tool_here
]

class RolesHeaderInterceptor:
    """Interceptor that injects user roles header into MCP tool calls."""

    def __init__(self, user_roles: list = None):
        self.user_roles = user_roles or []

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]]
    ) -> MCPToolCallResult:
        headers = dict(request.headers or {})
        if self.user_roles:
            headers["X-User-Roles"] = json.dumps(self.user_roles)

        modified_request = request.override(headers=headers)
        return await handler(modified_request)

def get_mcp_client(user_roles: list = None):
    """Create MCP client with user roles header."""
    return MultiServerMCPClient(
        {
            "cavepedia": {
                "transport": "streamable_http",
                "url": "https://mcp.caving.dev/mcp",
                "timeout": 10.0,
            }
        },
        tool_interceptors=[RolesHeaderInterceptor(user_roles)]
    )

# Cache for MCP tools per access token
_mcp_tools_cache = {}

async def get_mcp_tools(user_roles: list = None):
    """Lazy load MCP tools with user roles."""
    roles_key = ",".join(sorted(user_roles)) if user_roles else "default"

    if roles_key not in _mcp_tools_cache:
        try:
            mcp_client = get_mcp_client(user_roles)
            tools = await mcp_client.get_tools()
            _mcp_tools_cache[roles_key] = tools
            print(f"Loaded {len(tools)} tools from MCP server with roles: {user_roles}")
        except Exception as e:
            print(f"Warning: Failed to load MCP tools: {e}")
            _mcp_tools_cache[roles_key] = []

    return _mcp_tools_cache[roles_key]


async def chat_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Standard chat node based on the ReAct design pattern. It handles:
    - The model to use (and binds in CopilotKit actions and the tools defined above)
    - The system prompt
    - Getting a response from the model
    - Handling tool calls

    For more about the ReAct design pattern, see:
    https://www.perplexity.ai/search/react-agents-NcXLQhreS0WDzpVaS4m9Cg
    """

    # 0. Extract user roles from config.configurable.context
    configurable = config.get("configurable", {})
    context = configurable.get("context", {})
    user_roles = context.get("auth0_user_roles", [])

    # 1. Define the model
    model = ChatGoogleGenerativeAI(model="gemini-3-pro-preview", max_output_tokens=65536)

    # 1.5 Load MCP tools from the cavepedia server with roles
    mcp_tools = await get_mcp_tools(user_roles)

    # 2. Bind the tools to the model
    model_with_tools = model.bind_tools(
        [
            *state.get("tools", []),  # bind tools defined by ag-ui
            *backend_tools,
            *mcp_tools,  # Add MCP tools from cavepedia server
        ],
    )

    # 3. Define the system message by which the chat model will be run
    system_message = SystemMessage(
        content=f"""You are a helpful assistant with access to cave-related information through the Cavepedia MCP server. You can help users find information about caves, caving techniques, and related topics.

IMPORTANT RULES:
1. Always cite your sources at the end of each response. List the specific sources/documents you used.
2. If you cannot find information on a topic, say so clearly. Do NOT make up information or hallucinate facts.
3. If the MCP tools return no results, acknowledge that you couldn't find the information rather than guessing.

User roles: {', '.join(user_roles) if user_roles else 'none'}"""
    )

    # 4. Run the model to generate a response
    response = await model_with_tools.ainvoke(
        [
            system_message,
            *state["messages"],
        ],
        config,
    )

    # 5. Return the response in the messages
    return {"messages": [response]}


async def tool_node_wrapper(state: AgentState, config: RunnableConfig) -> dict:
    """
    Custom tool node that handles both backend tools and MCP tools.
    """
    # Extract user roles from config.configurable.context
    configurable = config.get("configurable", {})
    context = configurable.get("context", {})
    user_roles = context.get("auth0_user_roles", [])

    # Load MCP tools with roles
    mcp_tools = await get_mcp_tools(user_roles)
    all_tools = [*backend_tools, *mcp_tools]

    # Use the standard ToolNode with all tools
    node = ToolNode(tools=all_tools)
    result = await node.ainvoke(state, config)

    return result


# Define the workflow graph
workflow = StateGraph(AgentState)
workflow.add_node("chat_node", chat_node)
workflow.add_node("tools", tool_node_wrapper)  # Must be named "tools" for tools_condition

# Set entry point
workflow.add_edge(START, "chat_node")

# Use tools_condition for proper routing
workflow.add_conditional_edges(
    "chat_node",
    tools_condition,
)

# After tools execute, go back to chat
workflow.add_edge("tools", "chat_node")

graph = workflow.compile()
