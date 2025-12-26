"""
Cavepedia Discord Bot - Entry point.

A Discord bot that provides access to the Cavepedia AI assistant via /cavesearch command.
"""

import os
import sys
import logging

# Load environment variables BEFORE other imports
from dotenv import load_dotenv

load_dotenv()

# Set up JSON logging
from pythonjsonlogger import jsonlogger

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
handler = logging.StreamHandler()
handler.setFormatter(
    jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
)
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    handlers=[handler],
)
logger = logging.getLogger(__name__)

import discord
from discord import app_commands

from src.config import Config
from src.agent_client import AgentClient
from src.rate_limiter import RateLimiter


class CavepediaBot(discord.Client):
    """Discord bot for Cavepedia AI assistant."""

    def __init__(self, config: Config):
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.config = config
        self.tree = app_commands.CommandTree(self)
        self.agent_client = AgentClient(
            base_url=config.agent_url,
            default_roles=config.default_roles,
            sources_only=config.sources_only,
        )
        self.rate_limiter = RateLimiter(
            user_cooldown_seconds=config.rate_limit_user_seconds,
            global_per_minute=config.rate_limit_global_per_minute,
        )

    async def setup_hook(self):
        """Called when the bot is starting up."""
        await self.agent_client.start()

        # Register the cavesearch command (sources only)
        @self.tree.command(name="cavesearch", description="Search the caving knowledge base (sources only)")
        @app_commands.describe(query="Your question about caving")
        async def cavesearch(interaction: discord.Interaction, query: str):
            await self.handle_search(interaction, query, sources_only=True)

        # Register the cavechat command (full response)
        @self.tree.command(name="cavechat", description="Ask the caving AI assistant")
        @app_commands.describe(query="Your question about caving")
        async def cavechat(interaction: discord.Interaction, query: str):
            await self.handle_search(interaction, query, sources_only=False)

        # Sync commands to specific guilds for instant availability
        for guild_id in [1137321345718439959, 1454125232439955471]:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            try:
                await self.tree.sync(guild=guild)
                logger.info(f"Commands synced to guild {guild_id}")
            except discord.errors.Forbidden:
                logger.warning(f"No access to guild {guild_id}, skipping sync")
        logger.info("Bot setup complete")

    async def close(self):
        """Called when the bot is shutting down."""
        await self.agent_client.close()
        await super().close()

    async def on_ready(self):
        """Called when the bot has connected to Discord."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Allowed channels: {self.config.allowed_channels}")

        # Check agent health
        if await self.agent_client.health_check():
            logger.info("Agent server is healthy")
        else:
            logger.warning("Agent server health check failed")

    async def handle_search(self, interaction: discord.Interaction, query: str, sources_only: bool):
        """Handle the /cavesearch and /cavechat commands."""
        # Check if channel is allowed
        if interaction.channel_id not in self.config.allowed_channels:
            await interaction.response.send_message(
                "This command is not available in this channel.",
                ephemeral=True,
            )
            return

        # Check rate limits
        allowed, error_msg = self.rate_limiter.check(interaction.user.id)
        if not allowed:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        # Defer response since agent calls take time
        await interaction.response.defer()

        try:
            logger.info(
                f"Processing query from {interaction.user} in #{interaction.channel}: {query[:100]}..."
            )

            response = await self.agent_client.query(query, sources_only=sources_only)

            # Discord has a 2000 character limit
            if len(response) > 2000:
                chunks = self._split_response(response, max_length=1900)
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.channel.send(chunk)
            else:
                await interaction.followup.send(response)

            logger.info(f"Response sent to {interaction.user}")

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            await interaction.followup.send(
                "Sorry, I encountered an error processing your question. "
                "Please try again later."
            )

    def _split_response(self, text: str, max_length: int = 1900) -> list[str]:
        """Split a long response into chunks that fit Discord's limit."""
        chunks = []
        current_chunk = ""

        for line in text.split("\n"):
            if len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text[:max_length]]


def main():
    """Main entry point."""
    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    logger.info("Starting Cavepedia Discord bot...")
    logger.info(f"Agent URL: {config.agent_url}")
    logger.info(f"Allowed channels: {len(config.allowed_channels)}")
    logger.info(f"Default roles: {config.default_roles}")

    bot = CavepediaBot(config)
    bot.run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
