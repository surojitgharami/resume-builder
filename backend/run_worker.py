#!/usr/bin/env python
"""
Celery worker entrypoint script.

This script ensures proper environment initialization for Celery workers,
including loading environment variables and configuring logging.

Usage:
    python run_worker.py [celery worker options]

Examples:
    # Start worker with default concurrency
    python run_worker.py

    # Start worker with 4 concurrent processes
    python run_worker.py --concurrency=4

    # Start worker with beat scheduler
    python run_worker.py --beat

    # Start worker with specific log level
    python run_worker.py --loglevel=info
"""
import sys
import os
import logging

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging before importing app modules
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Start Celery worker with proper environment."""
    logger.info("Starting Celery worker...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"MongoDB URI: {os.getenv('MONGO_URI', 'not set').split('@')[-1] if '@' in os.getenv('MONGO_URI', '') else 'not set'}")
    logger.info(f"Redis URL: {os.getenv('REDIS_URL', 'not set')}")
    
    # Import Celery app (triggers worker initialization)
    from app.workers.celery_app import celery_app
    
    # Build command line arguments
    argv = [
        'worker',
        '--loglevel=info',
    ]
    
    # Add any additional arguments passed to the script
    if len(sys.argv) > 1:
        argv.extend(sys.argv[1:])
    
    logger.info(f"Starting worker with args: {' '.join(argv)}")
    
    # Start worker
    celery_app.worker_main(argv)


if __name__ == '__main__':
    main()
