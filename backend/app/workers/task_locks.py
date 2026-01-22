# app/workers/task_locks.py
import logging
from typing import Optional
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    import warnings
    warnings.warn("Redis not available. Task locking will use in-memory fallback.")

from app.core.config import settings

# In-memory fallback for task locks
_task_locks: dict = {}


class TaskLock:
    """Distributed task lock using Redis or in-memory fallback."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.use_redis = REDIS_AVAILABLE and settings.REDIS_URL
        
    async def connect(self):
        """Connect to Redis if available."""
        if not self.use_redis:
            logger.warning("Using in-memory task locking (not distributed)")
            return
        
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis for task locking")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            self.use_redis = False
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _get_lock_key(self, task_name: str, task_args: tuple) -> str:
        """Generate a unique lock key for a task with specific args."""
        # Create a hash of the task arguments for idempotency
        args_str = str(task_args)
        args_hash = hashlib.md5(args_str.encode()).hexdigest()
        return f"task_lock:{task_name}:{args_hash}"
    
    async def acquire(
        self,
        task_name: str,
        task_args: tuple,
        timeout_seconds: int = 3600
    ) -> bool:
        """
        Acquire a distributed lock for a task.
        
        Args:
            task_name: Name of the task
            task_args: Task arguments (for idempotency)
            timeout_seconds: Lock timeout in seconds
            
        Returns:
            True if lock acquired, False if already locked
        """
        lock_key = self._get_lock_key(task_name, task_args)
        
        if self.redis_client:
            return await self._acquire_redis(lock_key, timeout_seconds)
        else:
            return await self._acquire_memory(lock_key, timeout_seconds)
    
    async def release(self, task_name: str, task_args: tuple) -> bool:
        """
        Release a distributed lock.
        
        Args:
            task_name: Name of the task
            task_args: Task arguments
            
        Returns:
            True if lock released, False if lock didn't exist
        """
        lock_key = self._get_lock_key(task_name, task_args)
        
        if self.redis_client:
            return await self._release_redis(lock_key)
        else:
            return await self._release_memory(lock_key)
    
    async def is_locked(self, task_name: str, task_args: tuple) -> bool:
        """
        Check if a task is currently locked.
        
        Args:
            task_name: Name of the task
            task_args: Task arguments
            
        Returns:
            True if locked, False otherwise
        """
        lock_key = self._get_lock_key(task_name, task_args)
        
        if self.redis_client:
            result = await self.redis_client.get(lock_key)
            return result is not None
        else:
            if lock_key not in _task_locks:
                return False
            
            # Check if lock expired
            lock_data = _task_locks[lock_key]
            if datetime.utcnow() >= lock_data["expires_at"]:
                del _task_locks[lock_key]
                return False
            
            return True
    
    async def _acquire_redis(self, lock_key: str, timeout_seconds: int) -> bool:
        """Acquire lock using Redis."""
        try:
            # SET with NX (only if not exists) and EX (expiration)
            result = await self.redis_client.set(
                lock_key,
                datetime.utcnow().isoformat(),
                nx=True,
                ex=timeout_seconds
            )
            return result is not None
        except Exception as e:
            logger.error(f"Redis lock acquisition failed: {e}")
            return False
    
    async def _release_redis(self, lock_key: str) -> bool:
        """Release lock using Redis."""
        try:
            result = await self.redis_client.delete(lock_key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis lock release failed: {e}")
            return False
    
    async def _acquire_memory(self, lock_key: str, timeout_seconds: int) -> bool:
        """Acquire lock using in-memory cache."""
        now = datetime.utcnow()
        
        # Check if lock exists and is not expired
        if lock_key in _task_locks:
            lock_data = _task_locks[lock_key]
            if now < lock_data["expires_at"]:
                return False  # Lock already held
            else:
                # Lock expired, remove it
                del _task_locks[lock_key]
        
        # Acquire new lock
        _task_locks[lock_key] = {
            "acquired_at": now,
            "expires_at": now + timedelta(seconds=timeout_seconds)
        }
        return True
    
    async def _release_memory(self, lock_key: str) -> bool:
        """Release lock using in-memory cache."""
        if lock_key in _task_locks:
            del _task_locks[lock_key]
            return True
        return False


# Global task lock instance
task_lock = TaskLock()


async def with_task_lock(task_name: str, task_args: tuple, timeout_seconds: int = 3600):
    """
    Decorator to ensure task idempotency with distributed locking.
    
    Usage:
        @celery_app.task(bind=True)
        async def my_task(self, arg1, arg2):
            if not await with_task_lock("my_task", (arg1, arg2)):
                return {"status": "skipped", "reason": "already_running"}
            
            try:
                # Task logic here
                return {"status": "success"}
            finally:
                await task_lock.release("my_task", (arg1, arg2))
    """
    acquired = await task_lock.acquire(task_name, task_args, timeout_seconds)
    return acquired
