"""
Self-hosted PydanticAI agent server using AG-UI protocol.
"""

import os
import uvicorn
from dotenv import load_dotenv

from pydantic_ai.ui.ag_ui.app import AGUIApp
from main import agent

load_dotenv()

# Convert PydanticAI agent to ASGI app with AG-UI protocol
app = AGUIApp(agent)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
