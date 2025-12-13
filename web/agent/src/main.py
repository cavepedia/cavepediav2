"""
Self-hosted PydanticAI agent server using AG-UI protocol.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables BEFORE importing agent
load_dotenv()

# Set up logging based on environment
log_level = logging.DEBUG if os.getenv("DEBUG") else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Validate required environment variables
if not os.getenv("GOOGLE_API_KEY"):
    logger.error("GOOGLE_API_KEY environment variable is required")
    sys.exit(1)

import uvicorn
from src.agent import agent

logger.info("Creating AG-UI app...")

# Convert PydanticAI agent to ASGI app with AG-UI protocol
debug_mode = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
app = agent.to_ag_ui(debug=debug_mode)

logger.info("AG-UI app created successfully")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port)
