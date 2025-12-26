"""Configuration management for Discord bot."""

import os
import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Bot configuration from environment variables."""

    # Required
    discord_token: str
    agent_url: str
    allowed_channels: set[int]

    # Optional with defaults
    ambient_channels: set[int] = field(default_factory=set)
    default_roles: list[str] = field(default_factory=lambda: ["public"])
    sources_only: bool = False

    # Rate limiting
    rate_limit_user_seconds: int = 30
    rate_limit_global_per_minute: int = 20

    # Observability
    log_level: str = "INFO"
    environment: str = "development"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""

        # Required variables
        discord_token = os.environ.get("DISCORD_BOT_TOKEN")
        if not discord_token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")

        agent_url = os.environ.get("AGENT_URL")
        if not agent_url:
            raise ValueError("AGENT_URL environment variable is required")

        # Parse channel IDs
        allowed_channels_raw = os.environ.get("DISCORD_ALLOWED_CHANNELS", "[]")
        try:
            allowed_channels = set(int(c) for c in json.loads(allowed_channels_raw))
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid DISCORD_ALLOWED_CHANNELS: {e}")

        if not allowed_channels:
            raise ValueError(
                "DISCORD_ALLOWED_CHANNELS must contain at least one channel ID"
            )

        ambient_channels_raw = os.environ.get("DISCORD_AMBIENT_CHANNELS", "[]")
        try:
            ambient_channels = set(int(c) for c in json.loads(ambient_channels_raw))
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Invalid DISCORD_AMBIENT_CHANNELS, using empty: {e}")
            ambient_channels = set()

        # Parse roles
        default_roles_raw = os.environ.get("DISCORD_DEFAULT_ROLES", '["public"]')
        try:
            default_roles = json.loads(default_roles_raw)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid DISCORD_DEFAULT_ROLES, using ['public']: {e}")
            default_roles = ["public"]

        return cls(
            discord_token=discord_token,
            agent_url=agent_url,
            allowed_channels=allowed_channels,
            ambient_channels=ambient_channels,
            default_roles=default_roles,
            sources_only=os.environ.get("DISCORD_SOURCES_ONLY", "false").lower()
            == "true",
            rate_limit_user_seconds=int(
                os.environ.get("RATE_LIMIT_USER_SECONDS", "30")
            ),
            rate_limit_global_per_minute=int(
                os.environ.get("RATE_LIMIT_GLOBAL_PER_MINUTE", "20")
            ),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            environment=os.environ.get("ENVIRONMENT", "development"),
        )
