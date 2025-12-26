"""HTTP client for communicating with the PydanticAI agent server."""

import json
import logging
import uuid
import httpx

logger = logging.getLogger(__name__)


class AgentClient:
    """Client for the Cavepedia agent server."""

    def __init__(
        self, base_url: str, default_roles: list[str], sources_only: bool = False
    ):
        self.base_url = base_url.rstrip("/")
        self.default_roles = default_roles
        self.sources_only = sources_only
        self._client: httpx.AsyncClient | None = None

    async def start(self):
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(timeout=120.0)
        logger.info(f"Agent client initialized for {self.base_url}")

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        """Check if agent server is healthy."""
        if not self._client:
            return False
        try:
            response = await self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Agent health check failed: {e}")
            return False

    async def query(self, message: str) -> str:
        """
        Send a query to the agent and return the response.

        The agent uses AG-UI protocol with SSE streaming. We collect
        the full response for Discord (which doesn't support streaming).
        """
        if not self._client:
            raise RuntimeError("Agent client not initialized")

        headers = {
            "Content-Type": "application/json",
            "x-user-roles": json.dumps(self.default_roles),
            "x-sources-only": "true" if self.sources_only else "false",
        }

        # AG-UI protocol request format (RunAgentInput)
        payload = {
            "threadId": str(uuid.uuid4()),
            "runId": str(uuid.uuid4()),
            "state": {},
            "messages": [
                {
                    "id": str(uuid.uuid4()),
                    "role": "user",
                    "content": message,
                }
            ],
            "tools": [],
            "context": [],
            "forwardedProps": {},
        }

        try:
            response = await self._client.post(
                self.base_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            # Parse SSE response and extract text content
            return self._parse_agui_response(response.text)

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Agent request failed: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Agent request error: {e}")
            raise

    def _parse_agui_response(self, sse_text: str) -> str:
        """
        Parse AG-UI SSE response and extract the assistant's message.

        AG-UI sends events like:
        - TEXT_MESSAGE_START
        - TEXT_MESSAGE_CONTENT (with delta text)
        - TEXT_MESSAGE_END
        """
        content_parts = []

        for line in sse_text.split("\n"):
            if not line.startswith("data: "):
                continue

            try:
                data = json.loads(line[6:])  # Skip "data: " prefix

                # Handle TEXT_MESSAGE_CONTENT events
                if data.get("type") == "TEXT_MESSAGE_CONTENT":
                    delta = data.get("delta", "")
                    if delta:
                        content_parts.append(delta)

            except json.JSONDecodeError:
                continue

        result = "".join(content_parts)
        if not result:
            logger.warning("No content extracted from agent response")
            return "I couldn't generate a response. Please try again."

        return result
