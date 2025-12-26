"""Rate limiting for Discord bot."""

import time
import logging
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter using TTL caches."""

    def __init__(self, user_cooldown_seconds: int, global_per_minute: int):
        self.user_cooldown_seconds = user_cooldown_seconds
        self.global_per_minute = global_per_minute

        # Track last request time per user
        self._user_cache: TTLCache[int, float] = TTLCache(
            maxsize=10000, ttl=user_cooldown_seconds
        )

        # Track global requests in sliding window
        self._global_requests: list[float] = []

    def check(self, user_id: int) -> tuple[bool, str | None]:
        """
        Check if a request is allowed.

        Returns:
            (allowed, error_message) - If not allowed, includes reason
        """
        now = time.time()

        # Check user cooldown
        if user_id in self._user_cache:
            remaining = self.user_cooldown_seconds - (now - self._user_cache[user_id])
            if remaining > 0:
                return (
                    False,
                    f"Please wait {int(remaining)} seconds before asking another question.",
                )

        # Check global rate limit (clean old entries older than 60 seconds)
        self._global_requests = [t for t in self._global_requests if now - t < 60]

        if len(self._global_requests) >= self.global_per_minute:
            return (
                False,
                "The bot is receiving too many requests. Please try again in a minute.",
            )

        # Record this request
        self._user_cache[user_id] = now
        self._global_requests.append(now)

        return True, None
