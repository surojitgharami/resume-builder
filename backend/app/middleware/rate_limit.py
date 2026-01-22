# app/middleware/rate_limit.py
from fastapi import Request, HTTPException, status
from typing import Optional, Callable
import time
import hashlib
from functools import wraps
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory fallback for rate limiting (not recommended for production)
_rate_limit_cache: dict = {}


class RateLimiter:
    """Rate limiter using Redis or in-memory cache as fallback."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = settings.RATE_LIMIT_ENABLED
        
    async def connect(self):
        """
        Connect to Redis if available.
        
        Returns:
            bool: True if connected to Redis, False if using in-memory fallback
            
        Raises:
            Exception: Only if Redis connection fails unexpectedly (not if unavailable)
        """
        if not REDIS_AVAILABLE or not settings.REDIS_URL:
            logger.warning("Redis not available, using in-memory rate limiting")
            return False
        
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis for rate limiting")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    async def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if a key is rate limited.
        
        Args:
            key: Unique identifier for rate limiting
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_limited, current_count, retry_after_seconds)
        """
        if not self.enabled:
            return False, 0, 0
        
        if self.redis_client:
            return await self._check_redis(key, max_requests, window_seconds)
        else:
            return await self._check_memory(key, max_requests, window_seconds)
    
    async def _check_redis(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """Check rate limit using Redis."""
        try:
            current = await self.redis_client.get(key)
            
            if current is None:
                # First request
                await self.redis_client.setex(key, window_seconds, 1)
                return False, 1, 0
            
            count = int(current)
            
            if count >= max_requests:
                ttl = await self.redis_client.ttl(key)
                return True, count, max(ttl, 0)
            
            # Increment counter
            await self.redis_client.incr(key)
            return False, count + 1, 0
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return False, 0, 0
    
    async def _check_memory(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """Check rate limit using in-memory cache."""
        now = time.time()
        
        if key not in _rate_limit_cache:
            _rate_limit_cache[key] = {
                "count": 1,
                "reset_at": now + window_seconds
            }
            return False, 1, 0
        
        data = _rate_limit_cache[key]
        
        # Check if window has expired
        if now >= data["reset_at"]:
            _rate_limit_cache[key] = {
                "count": 1,
                "reset_at": now + window_seconds
            }
            return False, 1, 0
        
        # Check if limit exceeded
        if data["count"] >= max_requests:
            retry_after = int(data["reset_at"] - now)
            return True, data["count"], retry_after
        
        # Increment counter
        data["count"] += 1
        return False, data["count"], 0
    
    async def reset(self, key: str):
        """Reset rate limit for a key."""
        if self.redis_client:
            await self.redis_client.delete(key)
        elif key in _rate_limit_cache:
            del _rate_limit_cache[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_rate_limit_key(request: Request, identifier: str) -> str:
    """Generate a unique rate limit key."""
    client_ip = request.client.host if request.client else "unknown"
    return f"rate_limit:{identifier}:{client_ip}"


async def check_rate_limit(
    request: Request,
    identifier: str,
    max_requests: int,
    window_seconds: int
):
    """
    Check rate limit for a request.
    
    Args:
        request: FastAPI request object
        identifier: Rate limit identifier (e.g., "login", "resume_gen")
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    key = get_rate_limit_key(request, identifier)
    is_limited, count, retry_after = await rate_limiter.is_rate_limited(
        key, max_requests, window_seconds
    )
    
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + retry_after)
            }
        )
