# app/services/rag.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.services.embeddings import EmbeddingsService
from app.services.vector_store.factory import get_vector_store
from app.services.vector_store.base import VectorDocument
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """Service for Retrieval-Augmented Generation (RAG) functionality."""
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        embeddings_service: EmbeddingsService,
        use_vector_store: bool = True
    ):
        self.db = db
        self.embeddings_service = embeddings_service
        self.collection = db["rag_docs"]
        self.vector_index_name = "vector_index"
        
        # Initialize vector store adapter
        self.use_vector_store = use_vector_store and settings.VECTOR_STORE_PROVIDER
        if self.use_vector_store:
            try:
                self.vector_store = get_vector_store(db=db)
                logger.info(f"Using vector store: {settings.VECTOR_STORE_PROVIDER}")
            except Exception as e:
                logger.warning(f"Failed to initialize vector store: {e}. Falling back to MongoDB only.")
                self.use_vector_store = False
                self.vector_store = None
        else:
            self.vector_store = None
            logger.info("Vector store disabled, using MongoDB only")
    
    async def ingest_document(
        self,
        user_id: str,
        content: str,
        doc_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[str]:
        """
        Ingest a document into the RAG system with chunking and embedding.
        
        Stores in both MongoDB (for metadata) and vector store (for similarity search).
        
        Args:
            user_id: User ID who owns the document
            content: Document content
            doc_type: Type of document (resume, project, experience, etc.)
            metadata: Optional metadata dictionary
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of document IDs created
        """
        try:
            # Split content into chunks
            chunks = self._chunk_text(content, chunk_size, chunk_overlap)
            
            doc_ids = []
            vector_docs = []
            
            for i, chunk in enumerate(chunks):
                # Generate embedding for chunk
                embedding = await self.embeddings_service.generate_embedding(chunk)
                
                # Create document ID
                doc_id = str(uuid.uuid4())
                
                # Store in MongoDB (metadata + embedding)
                mongo_doc = {
                    "_id": doc_id,
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "content": chunk,
                    "embedding": embedding,
                    "doc_type": doc_type,
                    "chunk_index": i,
                    "metadata": metadata or {},
                    "created_at": datetime.utcnow()
                }
                await self.collection.insert_one(mongo_doc)
                
                # Prepare for vector store
                if self.use_vector_store:
                    vector_doc = VectorDocument(
                        id=doc_id,
                        content=chunk,
                        embedding=embedding,
                        metadata={
                            "user_id": user_id,
                            "doc_type": doc_type,
                            "chunk_index": i,
                            **(metadata or {})
                        },
                        created_at=datetime.utcnow()
                    )
                    vector_docs.append(vector_doc)
                
                doc_ids.append(doc_id)
            
            # Upsert to vector store in batch
            if self.use_vector_store and vector_docs:
                try:
                    await self.vector_store.upsert(
                        documents=vector_docs,
                        namespace=user_id  # Use user_id as namespace
                    )
                    logger.info(f"Upserted {len(vector_docs)} vectors to {settings.VECTOR_STORE_PROVIDER}")
                except Exception as e:
                    logger.warning(f"Vector store upsert failed: {e}. Data still in MongoDB.")
            
            logger.info(f"Ingested document with {len(chunks)} chunks for user {user_id}")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Failed to ingest document: {e}")
            raise Exception(f"Document ingestion failed: {str(e)}")
    
    async def search_similar(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.
        
        Uses vector store adapter if available, falls back to MongoDB.
        
        Args:
            user_id: User ID to search within
            query: Search query text
            top_k: Number of results to return
            doc_type: Optional filter by document type
            
        Returns:
            List of similar documents with scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embeddings_service.generate_embedding(query)
            
            # Try vector store first
            if self.use_vector_store:
                try:
                    filter_dict = {}
                    if doc_type:
                        filter_dict["doc_type"] = doc_type
                    
                    results = await self.vector_store.query(
                        embedding=query_embedding,
                        top_k=top_k,
                        filter_dict=filter_dict,
                        namespace=user_id
                    )
                    
                    logger.info(f"Found {len(results)} similar documents using {settings.VECTOR_STORE_PROVIDER}")
                    return results
                    
                except Exception as e:
                    logger.warning(f"Vector store search failed: {e}. Falling back to MongoDB.")
            
            # Fallback to MongoDB Atlas Vector Search
            return await self._mongodb_vector_search(user_id, query_embedding, top_k, doc_type)
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            # Final fallback to text search
            return await self._fallback_text_search(user_id, query, top_k, doc_type)
    
    async def _mongodb_vector_search(
        self,
        user_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """MongoDB Atlas Vector Search (original implementation)."""
        pipeline = []
        
        # MongoDB Atlas Vector Search
        search_stage = {
            "$search": {
                "index": self.vector_index_name,
                "knnBeta": {
                    "vector": query_embedding,
                    "path": "embedding",
                    "k": top_k * 2
                }
            }
        }
        pipeline.append(search_stage)
        
        # Add score
        pipeline.append({
            "$addFields": {
                "score": {"$meta": "searchScore"}
            }
        })
        
        # Filter by user
        match_filter = {"user_id": user_id}
        if doc_type:
            match_filter["doc_type"] = doc_type
        
        pipeline.append({"$match": match_filter})
        pipeline.append({"$limit": top_k})
        
        # Project relevant fields
        pipeline.append({
            "$project": {
                "doc_id": 1,
                "content": 1,
                "doc_type": 1,
                "metadata": 1,
                "score": 1
            }
        })
        
        # Execute search
        results = await self.collection.aggregate(pipeline).to_list(length=top_k)
        logger.info(f"Found {len(results)} similar documents using MongoDB Atlas")
        return results
    
    async def _fallback_text_search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fallback text search when vector search is not available."""
        try:
            match_filter = {
                "user_id": user_id,
                "$text": {"$search": query}
            }
            
            if doc_type:
                match_filter["doc_type"] = doc_type
            
            cursor = self.collection.find(
                match_filter,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(top_k)
            
            results = await cursor.to_list(length=top_k)
            return results
            
        except Exception as e:
            logger.error(f"Fallback text search failed: {e}")
            return []
    
    async def delete_user_documents(
        self,
        user_id: str,
        doc_type: Optional[str] = None
    ) -> int:
        """
        Delete all documents for a user from both MongoDB and vector store.
        
        Args:
            user_id: User ID
            doc_type: Optional filter by document type
            
        Returns:
            Number of documents deleted
        """
        # Delete from MongoDB
        filter_query = {"user_id": user_id}
        if doc_type:
            filter_query["doc_type"] = doc_type
        
        result = await self.collection.delete_many(filter_query)
        deleted_count = result.deleted_count
        
        # Delete from vector store
        if self.use_vector_store:
            try:
                filter_dict = {}
                if doc_type:
                    filter_dict["doc_type"] = doc_type
                
                await self.vector_store.delete_by_filter(
                    filter_dict=filter_dict,
                    namespace=user_id
                )
                logger.info(f"Deleted vectors from {settings.VECTOR_STORE_PROVIDER}")
            except Exception as e:
                logger.warning(f"Vector store delete failed: {e}")
        
        logger.info(f"Deleted {deleted_count} documents for user {user_id}")
        return deleted_count
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Input text
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                sentence_end = max(
                    text.rfind('. ', start, end),
                    text.rfind('! ', start, end),
                    text.rfind('? ', start, end),
                    text.rfind('\n', start, end)
                )
                
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - chunk_overlap
        
        return chunks


def get_rag_service(
    db: AsyncIOMotorDatabase,
    embeddings_service: EmbeddingsService
) -> RAGService:
    """Dependency to get RAG service instance."""
    return RAGService(db, embeddings_service)
