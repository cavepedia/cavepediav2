"""
Self-hosted LangGraph agent server using AG-UI protocol.
"""

import os
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from main import graph

load_dotenv()

app = FastAPI(title="Cavepedia Agent")

add_langgraph_fastapi_endpoint(
    app=app,
    agent=LangGraphAGUIAgent(
        name="vpi_1000",
        description="AI assistant with access to cave-related information through the Cavepedia MCP server",
        graph=graph,
    ),
    path="/",
)


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
