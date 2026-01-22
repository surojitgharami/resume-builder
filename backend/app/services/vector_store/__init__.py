# app/services/vector_store/__init__.py
"""
Vector store adapters for different providers.

Provides a unified interface for vector storage across multiple providers:
- MongoDB Atlas Vector Search
- Pinecone
- Qdrant
- Weaviate
- Chroma
"""
from .base import VectorStoreAdapter, VectorDocument
from .mongodb_adapter import MongoDBVectorAdapter
from .pinecone_adapter import PineconeAdapter
from .qdrant_adapter import QdrantAdapter
from .factory import get_vector_store

__all__ = [
    "VectorStoreAdapter",
    "VectorDocument",
    "MongoDBVectorAdapter",
    "PineconeAdapter",
    "QdrantAdapter",
    "get_vector_store",
]
