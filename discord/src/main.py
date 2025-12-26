"""
Cavepedia Discord Bot - Entry point.

A Discord bot that provides access to the Cavepedia AI assistant.
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

from src.config import Config
from src.agent_client import AgentClient
from src.rate_limiter import RateLimiter


class CavepediaBot(discord.Client):
    """Discord bot for Cavepedia AI assistant."""

    def __init__(self, config: Config):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        intents.guilds = True

        super().__init__(intents=intents)

        self.config = config
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
        logger.info("Bot setup complete")

    async def close(self):
        """Called when the bot is shutting down."""
        await self.agent_client.close()
        await super().close()

    async def on_ready(self):
        """Called when the bot has connected to Discord."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Allowed channels: {self.config.allowed_channels}")
        logger.info(f"Ambient channels: {self.config.ambient_channels}")

        # Check agent health
        if await self.agent_client.health_check():
            logger.info("Agent server is healthy")
        else:
            logger.warning("Agent server health check failed")

    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Ignore DMs
        if message.guild is None:
            return

        channel_id = message.channel.id

        # Check if this is an allowed channel
        if channel_id not in self.config.allowed_channels:
            return

        # Determine if we should respond
        is_ambient = channel_id in self.config.ambient_channels
        is_mentioned = self.user in message.mentions

        # In ambient channels, respond to all messages
        # In non-ambient allowed channels, only respond to mentions
        if not is_ambient and not is_mentioned:
            return

        # Extract the actual query (remove bot mention if present)
        query = message.content
        if is_mentioned:
            # Remove the mention from the message
            query = query.replace(f"<@{self.user.id}>", "").strip()
            query = query.replace(f"<@!{self.user.id}>", "").strip()

        # Skip empty messages
        if not query:
            await message.reply(
                "Please include a question after mentioning me. "
                "For example: @Cavepedia What is the deepest cave in Virginia?"
            )
            return

        # Check rate limits
        allowed, error_msg = self.rate_limiter.check(message.author.id)
        if not allowed:
            await message.reply(error_msg)
            return

        # Show typing indicator while processing
        async with message.channel.typing():
            try:
                logger.info(
                    f"Processing query from {message.author} in #{message.channel.name}: {query[:100]}..."
                )

                response = await self.agent_client.query(query)

                # Discord has a 2000 character limit
                if len(response) > 2000:
                    # Split into chunks, trying to break at newlines
                    chunks = self._split_response(response, max_length=1900)
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await message.reply(chunk)
                        else:
                            await message.channel.send(chunk)
                else:
                    await message.reply(response)

                logger.info(f"Response sent to {message.author}")

            except Exception as e:
                logger.error(f"Error processing query: {e}", exc_info=True)
                await message.reply(
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
    bot.run(config.discord_token, log_handler=None)  # We handle logging ourselves


if __name__ == "__main__":
    main()
