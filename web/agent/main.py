"""
This is the main entry point for the agent.
It defines the workflow graph, state, tools, nodes and edges.
"""

from typing import Any, List

from langchain.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, MessagesState, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command
from langchain_mcp_adapters.client import MultiServerMCPClient


class AgentState(MessagesState):
    """
    Here we define the state of the agent

    In this instance, we're inheriting from MessagesState, which will bring in
    the messages field for conversation history.
    """

    tools: List[Any]
    # your_custom_agent_state: str = ""


# @tool
# def your_tool_here(your_arg: str):
#     """Your tool description here."""
#     print(f"Your tool logic here")
#     return "Your tool response here."

backend_tools = [
    # your_tool_here
]

# Initialize MCP client
mcp_client = MultiServerMCPClient(
    {
        "cavepedia": {
            "transport": "streamable_http",
            "url": "https://mcp.caving.dev/mcp",
            "timeout": 10.0,
        }
    }
)

# Global variable to hold loaded MCP tools
_mcp_tools = None

async def get_mcp_tools():
    """Lazy load MCP tools on first access."""
    global _mcp_tools
    if _mcp_tools is None:
        try:
            _mcp_tools = await mcp_client.get_tools()
            print(f"Loaded {len(_mcp_tools)} tools from MCP server")
        except Exception as e:
            print(f"Warning: Failed to load MCP tools: {e}")
            _mcp_tools = []
    return _mcp_tools


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

    # 1. Define the model
    model = ChatAnthropic(model="claude-sonnet-4-5-20250929")

    # 1.5 Load MCP tools from the cavepedia server
    mcp_tools = await get_mcp_tools()

    # 2. Bind the tools to the model
    model_with_tools = model.bind_tools(
        [
            *state.get("tools", []),  # bind tools defined by ag-ui
            *backend_tools,
            *mcp_tools,  # Add MCP tools from cavepedia server
            # your_tool_here
        ],
        # 2.1 Disable parallel tool calls to avoid race conditions,
        #     enable this for faster performance if you want to manage
        #     the complexity of running tool calls in parallel.
        parallel_tool_calls=False,
    )

    # 3. Define the system message by which the chat model will be run
    system_message = SystemMessage(
        content="You are a helpful assistant with access to cave-related information through the Cavepedia MCP server. You can help users find information about caves, caving techniques, and related topics."
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


async def tool_node_wrapper(state: AgentState) -> dict:
    """
    Custom tool node that handles both backend tools and MCP tools.
    """
    # Load MCP tools and combine with backend tools
    mcp_tools = await get_mcp_tools()
    all_tools = [*backend_tools, *mcp_tools]

    # Use the standard ToolNode with all tools
    node = ToolNode(tools=all_tools)
    result = await node.ainvoke(state)

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
