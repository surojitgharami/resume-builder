#!/usr/bin/env python
"""
Celery beat scheduler entrypoint script.

This script starts the Celery beat scheduler for periodic tasks.

Usage:
    python run_beat.py [celery beat options]

Examples:
    # Start beat scheduler
    python run_beat.py

    # Start with specific log level
    python run_beat.py --loglevel=info
"""
import sys
import os
import logging

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Start Celery beat scheduler with proper environment."""
    logger.info("Starting Celery beat scheduler...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Import Celery app
    from app.workers.celery_app import celery_app
    
    # Build command line arguments
    argv = [
        'beat',
        '--loglevel=info',
    ]
    
    # Add any additional arguments
    if len(sys.argv) > 1:
        argv.extend(sys.argv[1:])
    
    logger.info(f"Starting beat with args: {' '.join(argv)}")
    
    # Start beat
    celery_app.start(argv)


if __name__ == '__main__':
    main()
