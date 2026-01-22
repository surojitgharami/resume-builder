# app/services/vector_store/factory.py
"""
Factory for creating vector store adapters based on configuration.

Supported Providers:
- mongodb_atlas: MongoDB Atlas with vector search (default)
- pinecone: Pinecone vector database
- qdrant: Qdrant vector database

Unsupported (Future):
- weaviate: Weaviate vector database (not implemented)
- chroma: ChromaDB (not implemented)

For unsupported providers, clear error messages guide configuration.
"""
import logging
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from .base import VectorStoreAdapter
from .mongodb_adapter import MongoDBVectorAdapter

logger = logging.getLogger(__name__)

# Supported providers with implementations
IMPLEMENTED_PROVIDERS = {
    "mongodb_atlas": "MongoDB Atlas with vector search",
    "pinecone": "Pinecone vector database",
    "qdrant": "Qdrant vector database",
}

# Future providers (not yet implemented)
UNIMPLEMENTED_PROVIDERS = {
    "weaviate": "Weaviate vector database",
    "chroma": "ChromaDB vector database",
}


def get_vector_store(
    db: Optional[AsyncIOMotorDatabase] = None,
    provider: Optional[str] = None
) -> VectorStoreAdapter:
    """
    Factory function to get the appropriate vector store adapter.
    
    Args:
        db: MongoDB database instance (required for MongoDB adapter)
        provider: Override the configured provider
        
    Returns:
        VectorStoreAdapter instance
        
    Raises:
        ValueError: If provider is not supported or required config is missing
    """
    provider = provider or settings.VECTOR_STORE_PROVIDER
    
    logger.info(f"Initializing vector store: {provider}")
    
    if provider == "mongodb_atlas":
        if db is None:
            raise ValueError("MongoDB database instance required for MongoDB adapter")
        
        return MongoDBVectorAdapter(
            db=db,
            collection_name=getattr(settings, 'VECTOR_COLLECTION_NAME', 'rag_docs')
        )
    
    elif provider == "pinecone":
        from .pinecone_adapter import PineconeAdapter
        
        api_key = getattr(settings, 'PINECONE_API_KEY', None)
        environment = getattr(settings, 'PINECONE_ENVIRONMENT', None)
        index_name = getattr(settings, 'PINECONE_INDEX_NAME', 'resume-vectors')
        
        if not api_key:
            raise ValueError("PINECONE_API_KEY not configured")
        if not environment:
            raise ValueError("PINECONE_ENVIRONMENT not configured")
        
        return PineconeAdapter(
            api_key=api_key,
            environment=environment,
            index_name=index_name
        )
    
    elif provider == "qdrant":
        from .qdrant_adapter import QdrantAdapter
        
        url = getattr(settings, 'QDRANT_URL', 'http://localhost:6333')
        api_key = getattr(settings, 'QDRANT_API_KEY', None)
        collection_name = getattr(settings, 'QDRANT_COLLECTION_NAME', 'resume_vectors')
        
        return QdrantAdapter(
            url=url,
            api_key=api_key,
            collection_name=collection_name
        )
    
    elif provider in UNIMPLEMENTED_PROVIDERS:
        # Provide helpful error message for unimplemented providers
        provider_name = UNIMPLEMENTED_PROVIDERS[provider]
        implemented_list = ", ".join(IMPLEMENTED_PROVIDERS.keys())
        
        error_msg = (
            f"Vector store provider '{provider}' ({provider_name}) is not yet implemented.\n\n"
            f"Supported providers: {implemented_list}\n\n"
            f"To use a supported provider, update your .env:\n"
            f"  VECTOR_STORE_PROVIDER=mongodb_atlas  # Default, uses MongoDB Atlas\n"
            f"  VECTOR_STORE_PROVIDER=pinecone       # Requires PINECONE_API_KEY\n"
            f"  VECTOR_STORE_PROVIDER=qdrant         # Requires QDRANT_URL\n\n"
            f"For {provider_name} support, please:\n"
            f"  1. Implement the adapter in app/services/vector_store/{provider}_adapter.py\n"
            f"  2. Update this factory to include the new adapter\n"
            f"  3. Add configuration settings to config.py"
        )
        
        logger.error(f"Attempted to use unimplemented provider: {provider}")
        raise NotImplementedError(error_msg)
    
    else:
        # Unknown provider
        all_providers = list(IMPLEMENTED_PROVIDERS.keys()) + list(UNIMPLEMENTED_PROVIDERS.keys())
        error_msg = (
            f"Unknown vector store provider: '{provider}'\n\n"
            f"Supported providers: {', '.join(IMPLEMENTED_PROVIDERS.keys())}\n"
            f"Future providers: {', '.join(UNIMPLEMENTED_PROVIDERS.keys())}\n\n"
            f"Update VECTOR_STORE_PROVIDER in your .env to one of: {', '.join(IMPLEMENTED_PROVIDERS.keys())}"
        )
        
        logger.error(f"Unknown vector store provider: {provider}")
        raise ValueError(error_msg)


def get_available_providers() -> List[str]:
    """
    Get list of implemented vector store providers.
    
    Returns:
        List of provider names that are currently implemented
    """
    return list(IMPLEMENTED_PROVIDERS.keys())


def get_all_providers() -> dict:
    """
    Get all known providers with their implementation status.
    
    Returns:
        Dict with 'implemented' and 'unimplemented' provider lists
    """
    return {
        "implemented": IMPLEMENTED_PROVIDERS,
        "unimplemented": UNIMPLEMENTED_PROVIDERS
    }


def is_provider_supported(provider: str) -> bool:
    """
    Check if a provider is supported (implemented).
    
    Args:
        provider: Provider name to check
        
    Returns:
        bool: True if provider is implemented, False otherwise
    """
    return provider in IMPLEMENTED_PROVIDERS


def validate_provider_config(provider: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """
    Validate vector store provider configuration.
    
    Args:
        provider: Provider name (defaults to settings.VECTOR_STORE_PROVIDER)
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if configuration is valid
        - (False, error_message) if configuration has issues
    """
    provider = provider or settings.VECTOR_STORE_PROVIDER
    
    # Check if provider is known
    if provider not in IMPLEMENTED_PROVIDERS and provider not in UNIMPLEMENTED_PROVIDERS:
        return False, f"Unknown provider: {provider}"
    
    # Check if provider is implemented
    if provider in UNIMPLEMENTED_PROVIDERS:
        return False, f"Provider '{provider}' is not yet implemented. Use: {', '.join(IMPLEMENTED_PROVIDERS.keys())}"
    
    # Check provider-specific configuration
    if provider == "mongodb_atlas":
        # MongoDB Atlas uses shared database connection
        return True, None
    
    elif provider == "pinecone":
        if not settings.PINECONE_API_KEY:
            return False, "PINECONE_API_KEY not configured"
        if not settings.PINECONE_ENVIRONMENT:
            return False, "PINECONE_ENVIRONMENT not configured"
        return True, None
    
    elif provider == "qdrant":
        if not settings.QDRANT_URL:
            return False, "QDRANT_URL not configured"
        return True, None
    
    return True, None
