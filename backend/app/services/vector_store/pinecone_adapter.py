# app/services/vector_store/pinecone_adapter.py
"""
Pinecone vector database adapter.
"""
import logging
from typing import List, Dict, Any, Optional

from .base import VectorStoreAdapter, VectorDocument

logger = logging.getLogger(__name__)

try:
    import pinecone
    from pinecone import Pinecone as PineconeClient
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.debug("Pinecone library not available")


class PineconeAdapter(VectorStoreAdapter):
    """Pinecone vector database adapter."""
    
    def __init__(self, api_key: str, environment: str, index_name: str):
        """
        Initialize Pinecone adapter.
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment (e.g., 'us-west1-gcp')
            index_name: Name of the Pinecone index
        """
        if not PINECONE_AVAILABLE:
            raise ImportError("Pinecone library not installed. Install with: pip install pinecone-client")
        
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        
        # Initialize Pinecone
        self.client = PineconeClient(api_key=api_key)
        self.index = self.client.Index(index_name)
        
        logger.info(f"Initialized Pinecone adapter for index: {index_name}")
    
    async def upsert(
        self,
        documents: List[VectorDocument],
        namespace: Optional[str] = None
    ) -> List[str]:
        """
        Upsert vectors into Pinecone.
        
        Args:
            documents: List of documents with embeddings
            namespace: Optional namespace
            
        Returns:
            List of document IDs
        """
        try:
            # Prepare vectors for Pinecone
            vectors = []
            for doc in documents:
                vector_data = {
                    "id": doc.id,
                    "values": doc.embedding,
                    "metadata": {
                        "content": doc.content[:1000],  # Pinecone has metadata size limits
                        **doc.metadata,
                        "created_at": doc.created_at.isoformat()
                    }
                }
                vectors.append(vector_data)
            
            # Upsert in batches (Pinecone recommends batch size of 100)
            batch_size = 100
            doc_ids = []
            
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch, namespace=namespace or "")
                doc_ids.extend([v["id"] for v in batch])
            
            logger.info(f"Upserted {len(doc_ids)} vectors to Pinecone")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Pinecone upsert failed: {e}")
            raise Exception(f"Failed to upsert to Pinecone: {str(e)}")
    
    async def query(
        self,
        embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query Pinecone for similar vectors.
        
        Args:
            embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            namespace: Optional namespace
            
        Returns:
            List of matching documents with scores
        """
        try:
            # Query Pinecone
            results = self.index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=namespace or "",
                filter=filter_dict
            )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                formatted_results.append({
                    "_id": match.id,
                    "content": match.metadata.get("content", ""),
                    "metadata": {k: v for k, v in match.metadata.items() if k != "content"},
                    "score": match.score
                })
            
            logger.info(f"Found {len(formatted_results)} similar vectors in Pinecone")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Pinecone query failed: {e}")
            raise Exception(f"Failed to query Pinecone: {str(e)}")
    
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> int:
        """
        Delete vectors from Pinecone by IDs.
        
        Args:
            ids: List of vector IDs
            namespace: Optional namespace
            
        Returns:
            Number of vectors deleted
        """
        try:
            self.index.delete(ids=ids, namespace=namespace or "")
            logger.info(f"Deleted {len(ids)} vectors from Pinecone")
            return len(ids)
            
        except Exception as e:
            logger.error(f"Pinecone delete failed: {e}")
            raise Exception(f"Failed to delete from Pinecone: {str(e)}")
    
    async def delete_by_filter(
        self,
        filter_dict: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> int:
        """
        Delete vectors by metadata filter.
        
        Args:
            filter_dict: Metadata filters
            namespace: Optional namespace
            
        Returns:
            Number of vectors deleted (approximate)
        """
        try:
            self.index.delete(filter=filter_dict, namespace=namespace or "")
            logger.info(f"Deleted vectors by filter from Pinecone")
            # Pinecone doesn't return exact count
            return 0
            
        except Exception as e:
            logger.error(f"Pinecone delete by filter failed: {e}")
            raise Exception(f"Failed to delete by filter: {str(e)}")
    
    async def get_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Pinecone index statistics.
        
        Args:
            namespace: Optional namespace
            
        Returns:
            Dictionary with statistics
        """
        try:
            stats = self.index.describe_index_stats()
            
            namespace_stats = stats.namespaces.get(namespace or "", {})
            
            return {
                "provider": "pinecone",
                "index_name": self.index_name,
                "dimension": stats.dimension,
                "total_vector_count": stats.total_vector_count,
                "namespace_vector_count": namespace_stats.get("vector_count", 0) if namespace else stats.total_vector_count,
                "namespace": namespace
            }
            
        except Exception as e:
            logger.error(f"Failed to get Pinecone stats: {e}")
            return {
                "provider": "pinecone",
                "error": str(e)
            }
    
    async def create_index(self, dimension: int = 768, metric: str = "cosine", pod_type: str = "p1.x1"):
        """
        Create a new Pinecone index.
        
        Args:
            dimension: Embedding dimension
            metric: Distance metric (cosine, euclidean, dotproduct)
            pod_type: Pinecone pod type
        """
        try:
            # Check if index exists
            existing_indexes = self.client.list_indexes()
            
            if self.index_name not in [idx.name for idx in existing_indexes]:
                self.client.create_index(
                    name=self.index_name,
                    dimension=dimension,
                    metric=metric,
                    spec={
                        "pod": {
                            "environment": self.environment,
                            "pod_type": pod_type
                        }
                    }
                )
                logger.info(f"Created Pinecone index: {self.index_name}")
            else:
                logger.info(f"Pinecone index already exists: {self.index_name}")
                
        except Exception as e:
            logger.error(f"Failed to create Pinecone index: {e}")
            raise Exception(f"Failed to create index: {str(e)}")
