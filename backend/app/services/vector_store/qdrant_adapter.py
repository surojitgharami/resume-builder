# app/services/vector_store/qdrant_adapter.py
"""
Qdrant vector database adapter.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import VectorStoreAdapter, VectorDocument

logger = logging.getLogger(__name__)

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.debug("Qdrant library not available")


class QdrantAdapter(VectorStoreAdapter):
    """Qdrant vector database adapter."""
    
    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        collection_name: str = "resume_vectors"
    ):
        """
        Initialize Qdrant adapter.
        
        Args:
            url: Qdrant server URL (e.g., 'http://localhost:6333' or cloud URL)
            api_key: Optional API key for Qdrant Cloud
            collection_name: Name of the collection
        """
        if not QDRANT_AVAILABLE:
            raise ImportError("Qdrant library not installed. Install with: pip install qdrant-client")
        
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        
        # Initialize Qdrant client
        self.client = QdrantClient(url=url, api_key=api_key)
        
        logger.info(f"Initialized Qdrant adapter for collection: {collection_name}")
    
    async def upsert(
        self,
        documents: List[VectorDocument],
        namespace: Optional[str] = None
    ) -> List[str]:
        """
        Upsert points into Qdrant.
        
        Args:
            documents: List of documents with embeddings
            namespace: Optional namespace (stored in payload)
            
        Returns:
            List of document IDs
        """
        try:
            # Prepare points for Qdrant
            points = []
            for doc in documents:
                payload = {
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "created_at": doc.created_at.isoformat(),
                    "namespace": namespace
                }
                
                point = PointStruct(
                    id=doc.id,
                    vector=doc.embedding,
                    payload=payload
                )
                points.append(point)
            
            # Upsert points
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            doc_ids = [doc.id for doc in documents]
            logger.info(f"Upserted {len(doc_ids)} points to Qdrant")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Qdrant upsert failed: {e}")
            raise Exception(f"Failed to upsert to Qdrant: {str(e)}")
    
    async def query(
        self,
        embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query Qdrant for similar vectors.
        
        Args:
            embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            namespace: Optional namespace filter
            
        Returns:
            List of matching documents with scores
        """
        try:
            # Build filter
            query_filter = None
            if filter_dict or namespace:
                conditions = []
                
                if namespace:
                    conditions.append(
                        FieldCondition(key="namespace", match=MatchValue(value=namespace))
                    )
                
                if filter_dict:
                    for key, value in filter_dict.items():
                        conditions.append(
                            FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))
                        )
                
                if conditions:
                    query_filter = Filter(must=conditions)
            
            # Search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=top_k,
                query_filter=query_filter
            )
            
            # Format results
            formatted_results = []
            for hit in search_result:
                formatted_results.append({
                    "_id": hit.id,
                    "content": hit.payload.get("content", ""),
                    "metadata": hit.payload.get("metadata", {}),
                    "score": hit.score,
                    "created_at": hit.payload.get("created_at")
                })
            
            logger.info(f"Found {len(formatted_results)} similar points in Qdrant")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Qdrant query failed: {e}")
            raise Exception(f"Failed to query Qdrant: {str(e)}")
    
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> int:
        """
        Delete points from Qdrant by IDs.
        
        Args:
            ids: List of point IDs
            namespace: Optional namespace filter (not used for direct ID deletion)
            
        Returns:
            Number of points deleted
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            
            logger.info(f"Deleted {len(ids)} points from Qdrant")
            return len(ids)
            
        except Exception as e:
            logger.error(f"Qdrant delete failed: {e}")
            raise Exception(f"Failed to delete from Qdrant: {str(e)}")
    
    async def delete_by_filter(
        self,
        filter_dict: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> int:
        """
        Delete points by filter.
        
        Args:
            filter_dict: Metadata filters
            namespace: Optional namespace filter
            
        Returns:
            Number of points deleted (approximate)
        """
        try:
            # Build filter
            conditions = []
            
            if namespace:
                conditions.append(
                    FieldCondition(key="namespace", match=MatchValue(value=namespace))
                )
            
            for key, value in filter_dict.items():
                conditions.append(
                    FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))
                )
            
            query_filter = Filter(must=conditions) if conditions else None
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=query_filter
            )
            
            logger.info(f"Deleted points by filter from Qdrant")
            return 0  # Qdrant doesn't return exact count
            
        except Exception as e:
            logger.error(f"Qdrant delete by filter failed: {e}")
            raise Exception(f"Failed to delete by filter: {str(e)}")
    
    async def get_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Qdrant collection statistics.
        
        Args:
            namespace: Optional namespace (not used in stats)
            
        Returns:
            Dictionary with statistics
        """
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            
            return {
                "provider": "qdrant",
                "collection_name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "dimension": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance.name
            }
            
        except Exception as e:
            logger.error(f"Failed to get Qdrant stats: {e}")
            return {
                "provider": "qdrant",
                "error": str(e)
            }
    
    async def create_index(self, dimension: int = 768, distance: str = "Cosine"):
        """
        Create a new Qdrant collection.
        
        Args:
            dimension: Embedding dimension
            distance: Distance metric (Cosine, Euclid, Dot)
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                # Map distance metric
                distance_map = {
                    "Cosine": Distance.COSINE,
                    "Euclid": Distance.EUCLID,
                    "Dot": Distance.DOT
                }
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=dimension,
                        distance=distance_map.get(distance, Distance.COSINE)
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection already exists: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to create Qdrant collection: {e}")
            raise Exception(f"Failed to create collection: {str(e)}")
