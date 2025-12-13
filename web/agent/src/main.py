"""
Self-hosted PydanticAI agent server using AG-UI protocol.
"""

import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables BEFORE importing agent
load_dotenv()

import uvicorn
from src.agent import agent

logger.info("Creating AG-UI app...")

# Convert PydanticAI agent to ASGI app with AG-UI protocol
app = agent.to_ag_ui(debug=True)

logger.info("AG-UI app created successfully")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
