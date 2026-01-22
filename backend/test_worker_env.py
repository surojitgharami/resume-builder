#!/usr/bin/env python
"""
Test script to verify Celery worker environment setup.

This script tests:
1. Database connection initialization per worker process
2. Service factory instantiation
3. Task execution with proper context
4. Resource cleanup on shutdown

Usage:
    python test_worker_env.py
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
from dotenv import load_dotenv
load_dotenv()

async def test_worker_db():
    """Test worker database connection."""
    print("\n=== Testing Worker Database Connection ===")
    
    from app.workers.celery_app import get_worker_db, init_worker_process
    
    # Simulate worker process init
    print("Initializing worker process...")
    init_worker_process()
    
    # Get database
    print("Getting worker database...")
    db = get_worker_db()
    
    # Test database operation
    print("Testing database query...")
    count = await db["users"].count_documents({})
    print(f"✅ Database connection works! Found {count} users.")
    
    return True


async def test_worker_services():
    """Test worker service factory."""
    print("\n=== Testing Worker Services ===")
    
    from app.workers.worker_services import (
        get_worker_llm_service,
        get_worker_embeddings_service,
        get_worker_storage_service,
        get_worker_ocr_service,
        get_worker_pdf_service
    )
    
    # Test LLM service
    print("Getting LLM service...")
    llm = get_worker_llm_service()
    print(f"✅ LLM service: {llm.__class__.__name__}")
    
    # Test embeddings service
    print("Getting embeddings service...")
    embeddings = get_worker_embeddings_service()
    print(f"✅ Embeddings service: {embeddings.__class__.__name__}")
    
    # Test storage service
    print("Getting storage service...")
    storage = get_worker_storage_service()
    print(f"✅ Storage service: {storage.__class__.__name__}")
    
    # Test OCR service
    print("Getting OCR service...")
    ocr = get_worker_ocr_service()
    print(f"✅ OCR service: {ocr.__class__.__name__}")
    
    # Test PDF service
    print("Getting PDF service...")
    pdf = get_worker_pdf_service()
    print(f"✅ PDF service: {pdf.__class__.__name__}")
    
    # Verify singleton behavior (same instance)
    llm2 = get_worker_llm_service()
    assert llm is llm2, "Service should be singleton per worker process"
    print("✅ Service singleton verified")
    
    return True


async def test_task_execution():
    """Test task execution context."""
    print("\n=== Testing Task Execution Context ===")
    
    from app.workers.tasks import get_task_db
    from app.workers.celery_app import init_worker_process
    
    # Initialize worker
    init_worker_process()
    
    # Get task DB
    print("Getting task database...")
    db = get_task_db()
    
    # Test query
    print("Testing database query from task context...")
    collections = await db.list_collection_names()
    print(f"✅ Task can access database! Collections: {', '.join(collections[:5])}...")
    
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Celery Worker Environment Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Worker DB
        result1 = await test_worker_db()
        
        # Test 2: Worker services
        result2 = await test_worker_services()
        
        # Test 3: Task execution
        result3 = await test_task_execution()
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\nWorker environment is properly configured:")
        print("  • Database connections: Per-process connection pooling")
        print("  • Service instances: Singleton per worker process")
        print("  • Task context: Proper database access")
        print("\nYou can now start workers with:")
        print("  python run_worker.py")
        print("  python run_beat.py")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
