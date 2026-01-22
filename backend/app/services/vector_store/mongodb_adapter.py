# app/services/vector_store/mongodb_adapter.py
"""
MongoDB Atlas Vector Search adapter.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from .base import VectorStoreAdapter, VectorDocument

logger = logging.getLogger(__name__)


class MongoDBVectorAdapter(VectorStoreAdapter):
    """MongoDB Atlas Vector Search adapter."""
    
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str = "rag_docs"):
        """
        Initialize MongoDB vector adapter.
        
        Args:
            db: MongoDB database instance
            collection_name: Name of collection to store vectors
        """
        self.db = db
        self.collection_name = collection_name
        self.collection = db[collection_name]
        self.vector_index_name = "vector_index"
    
    async def upsert(
        self,
        documents: List[VectorDocument],
        namespace: Optional[str] = None
    ) -> List[str]:
        """
        Upsert documents with embeddings into MongoDB.
        
        Args:
            documents: List of documents with embeddings
            namespace: Optional namespace (stored in metadata)
            
        Returns:
            List of document IDs
        """
        try:
            doc_ids = []
            
            for doc in documents:
                doc_dict = {
                    "_id": doc.id,
                    "content": doc.content,
                    "embedding": doc.embedding,
                    "metadata": {**doc.metadata, "namespace": namespace} if namespace else doc.metadata,
                    "created_at": doc.created_at,
                    "updated_at": datetime.utcnow()
                }
                
                # Upsert (update if exists, insert if not)
                await self.collection.replace_one(
                    {"_id": doc.id},
                    doc_dict,
                    upsert=True
                )
                
                doc_ids.append(doc.id)
            
            logger.info(f"Upserted {len(doc_ids)} documents to MongoDB")
            return doc_ids
            
        except Exception as e:
            logger.error(f"MongoDB upsert failed: {e}")
            raise Exception(f"Failed to upsert to MongoDB: {str(e)}")
    
    async def query(
        self,
        embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for similar vectors using MongoDB Atlas Vector Search.
        
        Args:
            embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            namespace: Optional namespace filter
            
        Returns:
            List of matching documents with scores
        """
        try:
            # Build aggregation pipeline for vector search
            pipeline = []
            
            # Vector search stage (MongoDB Atlas specific)
            search_stage = {
                "$search": {
                    "index": self.vector_index_name,
                    "knnBeta": {
                        "vector": embedding,
                        "path": "embedding",
                        "k": top_k * 2  # Get more for filtering
                    }
                }
            }
            
            # Add pre-filter if using MongoDB Atlas Search with filter support
            if filter_dict or namespace:
                filter_query = {}
                if namespace:
                    filter_query["metadata.namespace"] = namespace
                if filter_dict:
                    for key, value in filter_dict.items():
                        filter_query[f"metadata.{key}"] = value
                
                if filter_query:
                    search_stage["$search"]["knnBeta"]["filter"] = filter_query
            
            pipeline.append(search_stage)
            
            # Add score
            pipeline.append({
                "$addFields": {
                    "score": {"$meta": "searchScore"}
                }
            })
            
            # Post-filter if needed
            if filter_dict or namespace:
                match_filter = {}
                if namespace:
                    match_filter["metadata.namespace"] = namespace
                if filter_dict:
                    for key, value in filter_dict.items():
                        match_filter[f"metadata.{key}"] = value
                
                if match_filter:
                    pipeline.append({"$match": match_filter})
            
            # Limit results
            pipeline.append({"$limit": top_k})
            
            # Project fields
            pipeline.append({
                "$project": {
                    "_id": 1,
                    "content": 1,
                    "metadata": 1,
                    "score": 1,
                    "created_at": 1
                }
            })
            
            # Execute search
            results = await self.collection.aggregate(pipeline).to_list(length=top_k)
            
            logger.info(f"Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            logger.error(f"MongoDB vector search failed: {e}")
            # Fallback to text search
            return await self._fallback_text_search(embedding, top_k, filter_dict, namespace)
    
    async def _fallback_text_search(
        self,
        embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fallback to text search if vector search fails."""
        try:
            match_filter = {}
            if namespace:
                match_filter["metadata.namespace"] = namespace
            if filter_dict:
                for key, value in filter_dict.items():
                    match_filter[f"metadata.{key}"] = value
            
            cursor = self.collection.find(match_filter).limit(top_k)
            results = await cursor.to_list(length=top_k)
            
            # Add dummy score
            for result in results:
                result["score"] = 0.5
            
            return results
            
        except Exception as e:
            logger.error(f"Fallback text search failed: {e}")
            return []
    
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> int:
        """
        Delete documents by IDs.
        
        Args:
            ids: List of document IDs
            namespace: Optional namespace filter
            
        Returns:
            Number of documents deleted
        """
        try:
            filter_query = {"_id": {"$in": ids}}
            if namespace:
                filter_query["metadata.namespace"] = namespace
            
            result = await self.collection.delete_many(filter_query)
            logger.info(f"Deleted {result.deleted_count} documents from MongoDB")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"MongoDB delete failed: {e}")
            raise Exception(f"Failed to delete from MongoDB: {str(e)}")
    
    async def delete_by_filter(
        self,
        filter_dict: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> int:
        """
        Delete documents by metadata filter.
        
        Args:
            filter_dict: Metadata filters
            namespace: Optional namespace filter
            
        Returns:
            Number of documents deleted
        """
        try:
            mongo_filter = {}
            if namespace:
                mongo_filter["metadata.namespace"] = namespace
            
            for key, value in filter_dict.items():
                mongo_filter[f"metadata.{key}"] = value
            
            result = await self.collection.delete_many(mongo_filter)
            logger.info(f"Deleted {result.deleted_count} documents by filter")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"MongoDB delete by filter failed: {e}")
            raise Exception(f"Failed to delete by filter: {str(e)}")
    
    async def get_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Args:
            namespace: Optional namespace filter
            
        Returns:
            Dictionary with statistics
        """
        try:
            filter_query = {}
            if namespace:
                filter_query["metadata.namespace"] = namespace
            
            count = await self.collection.count_documents(filter_query)
            
            # Get average embedding size
            sample = await self.collection.find_one(filter_query)
            embedding_dim = len(sample["embedding"]) if sample and "embedding" in sample else 0
            
            return {
                "provider": "mongodb",
                "collection": self.collection_name,
                "document_count": count,
                "embedding_dimension": embedding_dim,
                "namespace": namespace
            }
            
        except Exception as e:
            logger.error(f"Failed to get MongoDB stats: {e}")
            return {
                "provider": "mongodb",
                "error": str(e)
            }
    
    async def create_index(self, dimension: int = 768, similarity: str = "cosine"):
        """
        Create vector search index in MongoDB Atlas.
        
        Note: This requires MongoDB Atlas with vector search enabled.
        Index creation is typically done via Atlas UI or API.
        
        Args:
            dimension: Embedding dimension
            similarity: Similarity metric (cosine, euclidean, dotProduct)
        """
        logger.info(
            f"MongoDB Atlas vector index should be created via Atlas UI. "
            f"Index name: {self.vector_index_name}, "
            f"Field: embedding, "
            f"Dimension: {dimension}, "
            f"Similarity: {similarity}"
        )
        
        # Create text index as fallback
        try:
            await self.collection.create_index([("content", "text")])
            logger.info("Created text index on content field")
        except Exception as e:
            logger.warning(f"Failed to create text index: {e}")
