# app/db/mongo.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global MongoDB client instance
_mongo_client: Optional[AsyncIOMotorClient] = None


async def connect_to_mongo():
    """
    Create MongoDB Atlas connection pool.
    
    PRODUCTION MODE: MongoDB Atlas is REQUIRED. Application will fail on startup
    if connection cannot be established.
    
    Connection parameters optimized for MongoDB Atlas:
    - retryWrites=true (default for Atlas)
    - w=majority (write concern for durability)
    - serverSelectionTimeoutMS: 10 seconds (Atlas recommendation)
    - connectTimeoutMS: 20 seconds (Atlas recommendation)
    
    Raises:
        Exception: If connection to MongoDB Atlas fails
    """
    global _mongo_client
    
    try:
        # Mask password in logs for security
        mongo_uri_display = settings.MONGO_URI
        if '@' in mongo_uri_display:
            parts = mongo_uri_display.split('@')
            if '://' in parts[0]:
                protocol = parts[0].split('://')[0]
                mongo_uri_display = f"{protocol}://***:***@{parts[1]}"
        
        logger.info(f"Connecting to MongoDB Atlas: {settings.MONGO_DB_NAME}")
        logger.info(f"Connection URI: {mongo_uri_display}")
        
        # Create Motor client with Atlas-optimized settings
        _mongo_client = AsyncIOMotorClient(
            settings.MONGO_URI,
            minPoolSize=settings.MONGO_MIN_POOL_SIZE,
            maxPoolSize=settings.MONGO_MAX_POOL_SIZE,
            serverSelectionTimeoutMS=10000,  # 10 seconds for Atlas
            connectTimeoutMS=20000,           # 20 seconds for Atlas
            socketTimeoutMS=45000,            # 45 seconds for operations
            retryWrites=True,                 # Enable retryable writes (Atlas default)
            w='majority',                     # Write concern for durability
            retryReads=True,                  # Enable retryable reads
            appName='ai-resume-builder'       # Application name for Atlas monitoring
        )
        
        # Test connection with timeout
        logger.info("Testing MongoDB Atlas connection...")
        await _mongo_client.admin.command('ping')
        
        # Get server info for validation
        server_info = await _mongo_client.server_info()
        logger.info(f"Successfully connected to MongoDB Atlas")
        logger.info(f"MongoDB version: {server_info.get('version', 'unknown')}")
        logger.info(f"Database: {settings.MONGO_DB_NAME}")
        
    except Exception as e:
        logger.critical(f"FATAL: Failed to connect to MongoDB Atlas: {str(e)}")
        logger.critical("Application cannot start without MongoDB Atlas connection.")
        logger.critical("Please check:")
        logger.critical("  1. MONGO_URI is correctly set in .env")
        logger.critical("  2. IP address is whitelisted in Atlas Network Access")
        logger.critical("  3. Database user credentials are correct")
        logger.critical("  4. Atlas cluster is running and accessible")
        
        # Clean up on failure
        if _mongo_client:
            _mongo_client.close()
            _mongo_client = None
        
        # Always fail - MongoDB Atlas is required
        raise RuntimeError(f"MongoDB Atlas connection failed: {str(e)}") from e


async def close_mongo_connection():
    """
    Close MongoDB client connection.
    Should be called on application shutdown.
    """
    global _mongo_client
    
    if _mongo_client:
        logger.info("Closing MongoDB connection")
        _mongo_client.close()
        _mongo_client = None


def get_database() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance.
    
    Returns:
        AsyncIOMotorDatabase instance
    
    Raises:
        RuntimeError: If database connection not initialized
    """
    if _mongo_client is None:
        raise RuntimeError("Database connection not initialized. Call connect_to_mongo() first.")
    
    return _mongo_client[settings.MONGO_DB_NAME]


async def get_collection(collection_name: str):
    """
    Get MongoDB collection instance.
    
    Args:
        collection_name: Name of the collection
    
    Returns:
        AsyncIOMotorCollection instance
    """
    db = get_database()
    return db[collection_name]


async def create_indexes():
    """
    Create all required database indexes.
    Should be called after database connection is established.
    
    Handles IndexOptionsConflict gracefully for idempotent deployments.
    """
    db = get_database()
    
    async def safe_create_index(collection, *args, **kwargs):
        """
        Create index with graceful handling of IndexOptionsConflict.
        
        This handles the case where an index already exists with different options,
        which commonly happens with TTL indexes when code is redeployed.
        """
        try:
            await collection.create_index(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            # Check for index conflict (code 85 or error message)
            if "IndexOptionsConflict" in error_str or "code': 85" in error_str:
                index_name = kwargs.get('name') or str(args[0])
                logger.warning(f"Index '{index_name}' already exists with different options. Skipping.")
            else:
                # Re-raise if it's not an index conflict
                raise
    
    try:
        logger.info("Creating database indexes")
        
        # Users collection indexes
        await safe_create_index(db.users, "email", unique=True)
        await safe_create_index(db.users, "auth.last_login")
        await safe_create_index(db.users, "created_at")
        
        # Refresh tokens collection indexes
        await safe_create_index(db.refresh_tokens, "refresh_token_hash", unique=True)
        await safe_create_index(db.refresh_tokens, [("user_id", 1), ("revoked", 1)])
        await safe_create_index(db.refresh_tokens, "expires_at", expireAfterSeconds=0)
        
        # Resumes collection indexes
        await safe_create_index(db.resumes, "resume_id", unique=True)
        await safe_create_index(db.resumes, [("user_id", 1), ("generated_at", -1)])
        await safe_create_index(db.resumes, [("user_id", 1), ("status", 1)])
        
        # Projects collection indexes
        await safe_create_index(db.projects, [("user_id", 1), ("created_at", -1)])
        await safe_create_index(db.projects, [("user_id", 1), ("technologies", 1)])
        
        # Job matches collection indexes
        await safe_create_index(db.job_matches, [("user_id", 1), ("match_score", -1)])
        await safe_create_index(db.job_matches, [("user_id", 1), ("status", 1), ("created_at", -1)])
        await safe_create_index(db.job_matches, [("user_id", 1), ("company", 1)])
        
        # RAG docs collection indexes
        await safe_create_index(db.rag_docs, "doc_id")
        await safe_create_index(db.rag_docs, [("user_id", 1), ("doc_type", 1)])
        await safe_create_index(db.rag_docs, [("doc_type", 1), ("created_at", -1)])
        
        # Audit logs collection indexes
        await safe_create_index(db.audit_logs, [("user_id", 1), ("timestamp", -1)])
        await safe_create_index(db.audit_logs, [("event_type", 1), ("timestamp", -1)])
        
        # TTL index for audit logs - 90 days retention
        # Note: If this conflicts, the existing index will be used
        await safe_create_index(
            db.audit_logs,
            [("timestamp", 1)],
            name="timestamp_ttl",
            expireAfterSeconds=7776000  # 90 days
        )
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {str(e)}")
        raise


async def health_check() -> bool:
    """
    Check if MongoDB connection is healthy.
    
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        if _mongo_client is None:
            return False
        
        await _mongo_client.admin.command('ping')
        return True
    
    except Exception as e:
        logger.error(f"MongoDB health check failed: {str(e)}")
        return False
