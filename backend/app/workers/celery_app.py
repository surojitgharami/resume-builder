# app/workers/celery_app.py
"""
Celery task queue configuration for AI Resume Builder.

This module provides Celery configuration with proper Redis fallback handling:
- Uses CELERY_BROKER_URL if set
- Falls back to REDIS_URL if broker not explicitly configured
- Supports CELERY_TASK_ALWAYS_EAGER for development without Redis
- Provides clear warnings when broker is not configured

Configuration:
    Production (with Redis):
        CELERY_BROKER_URL=redis://redis-host:6379/0
        CELERY_RESULT_BACKEND=redis://redis-host:6379/0
    
    Development (without Redis):
        CELERY_TASK_ALWAYS_EAGER=true
        # Tasks execute synchronously in the same process
"""

import logging
from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown, worker_init
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import warnings

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_broker_url() -> Optional[str]:
    """
    Get Celery broker URL with proper fallback logic.
    
    Priority:
    1. CELERY_BROKER_URL (explicit broker configuration)
    2. REDIS_URL (shared Redis instance)
    3. None (will trigger warning)
    
    Returns:
        str or None: Broker URL
    """
    broker = settings.CELERY_BROKER_URL or settings.REDIS_URL
    
    if not broker:
        if settings.CELERY_TASK_ALWAYS_EAGER:
            logger.info("No broker configured. Running tasks in EAGER mode (synchronous).")
        else:
            logger.warning(
                "No Celery broker configured (CELERY_BROKER_URL or REDIS_URL). "
                "Tasks will fail unless CELERY_TASK_ALWAYS_EAGER=true. "
                "For production, set CELERY_BROKER_URL or REDIS_URL."
            )
            warnings.warn(
                "Celery broker not configured. Set CELERY_BROKER_URL, REDIS_URL, or CELERY_TASK_ALWAYS_EAGER=true",
                UserWarning
            )
    
    return broker


def _get_result_backend() -> Optional[str]:
    """
    Get Celery result backend URL with proper fallback logic.
    
    Priority:
    1. CELERY_RESULT_BACKEND (explicit backend configuration)
    2. CELERY_BROKER_URL (same as broker)
    3. REDIS_URL (shared Redis instance)
    4. None (tasks won't store results)
    
    Returns:
        str or None: Result backend URL
    """
    backend = settings.CELERY_RESULT_BACKEND or settings.CELERY_BROKER_URL or settings.REDIS_URL
    
    if not backend and not settings.CELERY_TASK_ALWAYS_EAGER:
        logger.warning("No result backend configured. Task results won't be stored.")
    
    return backend


# Get broker and backend URLs
broker_url = _get_broker_url()
backend_url = _get_result_backend()

# Create Celery app
celery_app = Celery(
    "resume_builder_tasks",
    broker=broker_url,
    backend=backend_url
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    imports=('app.workers.tasks',),  # Auto-discover tasks
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,  # Execute synchronously in dev
    task_eager_propagates=True,  # Propagate exceptions in eager mode
)

# Log configuration
if settings.CELERY_TASK_ALWAYS_EAGER:
    logger.info("Celery configured in EAGER mode - tasks run synchronously (development)")
else:
    if broker_url:
        # Mask credentials in log
        safe_broker = broker_url
        if '@' in safe_broker:
            parts = safe_broker.split('@')
            safe_broker = f"***:***@{parts[-1]}"
        logger.info(f"Celery broker configured: {safe_broker}")
    else:
        logger.error("Celery broker NOT configured - tasks will fail!")

# Global worker state (per-process)
_worker_db_client: Optional[AsyncIOMotorClient] = None
_worker_db = None


def get_worker_db():
    """
    Get database connection for the current worker process.
    
    This is thread-safe and creates one connection pool per worker process.
    """
    global _worker_db
    if _worker_db is None:
        raise RuntimeError("Worker database not initialized. Use worker_process_init signal.")
    return _worker_db


@worker_process_init.connect
def init_worker_process(**kwargs):
    """
    Initialize worker process with fresh database connections.
    
    This is called once per worker process (not per task).
    Creates a new connection pool for this worker process.
    """
    global _worker_db_client, _worker_db
    
    logger.info(f"Initializing worker process {kwargs.get('sender')}")
    
    try:
        # Create fresh MongoDB client for this worker process
        _worker_db_client = AsyncIOMotorClient(
            settings.MONGO_URI,
            minPoolSize=settings.MONGO_MIN_POOL_SIZE,
            maxPoolSize=settings.MONGO_MAX_POOL_SIZE,
            serverSelectionTimeoutMS=5000
        )
        _worker_db = _worker_db_client[settings.MONGO_DB_NAME]
        
        logger.info("Worker database connection initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize worker database: {e}")
        raise


@worker_process_shutdown.connect
def shutdown_worker_process(**kwargs):
    """
    Clean up worker process resources.
    
    Closes database connections when worker process shuts down.
    """
    global _worker_db_client, _worker_db
    
    logger.info(f"Shutting down worker process {kwargs.get('sender')}")
    
    try:
        if _worker_db_client:
            _worker_db_client.close()
            _worker_db_client = None
            _worker_db = None
            logger.info("Worker database connection closed")
            
    except Exception as e:
        logger.error(f"Error closing worker database: {e}")


@worker_init.connect
def init_worker(**kwargs):
    """
    Initialize worker (called once per worker, not per process).
    
    Use this for worker-level initialization.
    """
    logger.info(f"Worker {kwargs.get('sender')} initialized")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info(f"MongoDB: {settings.MONGO_URI.split('@')[-1] if '@' in settings.MONGO_URI else settings.MONGO_URI}")


logger.info("Celery app initialized")
