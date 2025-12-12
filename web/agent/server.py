"""
Self-hosted LangGraph agent server using CopilotKit.
"""

import os
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from main import graph

load_dotenv()

app = FastAPI(title="Cavepedia Agent")


def build_agents(context):
    """Build agents with auth context from properties."""
    # Get user roles from frontend properties
    user_roles = context.get("properties", {}).get("auth0_user_roles", [])

    return [
        LangGraphAgent(
            name="vpi_1000",
            description="AI assistant with access to cave-related information through the Cavepedia MCP server",
            graph=graph,
            langgraph_config={
                "configurable": {
                    "context": {
                        "auth0_user_roles": user_roles,
                    }
                }
            },
        )
    ]


sdk = CopilotKitRemoteEndpoint(agents=build_agents)
add_fastapi_endpoint(app, sdk, "/copilotkit")


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
