# app/services/vector_store/base.py
"""
Base class for vector store adapters.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class VectorDocument(BaseModel):
    """Document with vector embedding."""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VectorStoreAdapter(ABC):
    """Abstract base class for vector store adapters."""
    
    @abstractmethod
    async def upsert(
        self,
        documents: List[VectorDocument],
        namespace: Optional[str] = None
    ) -> List[str]:
        """
        Insert or update documents with embeddings.
        
        Args:
            documents: List of documents with embeddings
            namespace: Optional namespace/collection name
            
        Returns:
            List of document IDs that were upserted
        """
        pass
    
    @abstractmethod
    async def query(
        self,
        embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for similar vectors.
        
        Args:
            embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            namespace: Optional namespace/collection name
            
        Returns:
            List of matching documents with scores
        """
        pass
    
    @abstractmethod
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> int:
        """
        Delete documents by IDs.
        
        Args:
            ids: List of document IDs to delete
            namespace: Optional namespace/collection name
            
        Returns:
            Number of documents deleted
        """
        pass
    
    @abstractmethod
    async def delete_by_filter(
        self,
        filter_dict: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> int:
        """
        Delete documents by metadata filter.
        
        Args:
            filter_dict: Metadata filters
            namespace: Optional namespace/collection name
            
        Returns:
            Number of documents deleted
        """
        pass
    
    @abstractmethod
    async def get_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Args:
            namespace: Optional namespace/collection name
            
        Returns:
            Dictionary with statistics
        """
        pass
    
    async def create_index(self, **kwargs):
        """
        Create vector index (if needed).
        Some providers require explicit index creation.
        """
        pass
