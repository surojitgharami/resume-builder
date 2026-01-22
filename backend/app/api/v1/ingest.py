# app/api/v1/ingest.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from typing import Optional, List

from app.models.user import User
from app.middleware.auth import get_current_active_user
from app.middleware.rate_limit import check_rate_limit
from app.db.mongo import get_database
from app.services.rag import RAGService
from app.services.embeddings import get_embeddings_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class IngestRequest(BaseModel):
    content: str = Field(min_length=10, max_length=50000)
    doc_type: str = Field(default="general")
    metadata: Optional[dict] = None
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)


class IngestResponse(BaseModel):
    document_ids: List[str]
    chunks_created: int
    message: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    doc_type: Optional[str] = None


class SearchResult(BaseModel):
    doc_id: str
    content: str
    doc_type: str
    score: Optional[float] = None
    metadata: Optional[dict] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    total_results: int


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    request: Request,
    ingest_request: IngestRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Ingest a document into the RAG system for semantic search.
    
    Args:
        request: FastAPI request object
        ingest_request: Document ingestion request
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        Ingestion response with document IDs
        
    Raises:
        HTTPException: If ingestion fails
    """
    # Rate limiting
    await check_rate_limit(
        request,
        "document_ingest",
        max_requests=50,
        window_seconds=3600
    )
    
    try:
        embeddings_service = get_embeddings_service()
        rag_service = RAGService(db, embeddings_service)
        
        doc_ids = await rag_service.ingest_document(
            user_id=str(current_user.id),
            content=ingest_request.content,
            doc_type=ingest_request.doc_type,
            metadata=ingest_request.metadata,
            chunk_size=ingest_request.chunk_size,
            chunk_overlap=ingest_request.chunk_overlap
        )
        
        logger.info(f"Ingested document with {len(doc_ids)} chunks for user {current_user.id}")
        
        return IngestResponse(
            document_ids=doc_ids,
            chunks_created=len(doc_ids),
            message=f"Successfully ingested document with {len(doc_ids)} chunks"
        )
        
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: Request,
    search_request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Search for similar documents using semantic search.
    
    Args:
        request: FastAPI request object
        search_request: Search request
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        Search results
        
    Raises:
        HTTPException: If search fails
    """
    # Rate limiting
    await check_rate_limit(
        request,
        "document_search",
        max_requests=100,
        window_seconds=3600
    )
    
    try:
        embeddings_service = get_embeddings_service()
        rag_service = RAGService(db, embeddings_service)
        
        results = await rag_service.search_similar(
            user_id=str(current_user.id),
            query=search_request.query,
            top_k=search_request.top_k,
            doc_type=search_request.doc_type
        )
        
        search_results = [
            SearchResult(
                doc_id=result["doc_id"],
                content=result["content"],
                doc_type=result["doc_type"],
                score=result.get("score"),
                metadata=result.get("metadata")
            )
            for result in results
        ]
        
        return SearchResponse(
            results=search_results,
            query=search_request.query,
            total_results=len(search_results)
        )
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document search failed: {str(e)}"
        )


@router.delete("/documents", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_documents(
    doc_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete all documents for the current user.
    
    Args:
        doc_type: Optional filter by document type
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        None
    """
    try:
        embeddings_service = get_embeddings_service()
        rag_service = RAGService(db, embeddings_service)
        
        deleted_count = await rag_service.delete_user_documents(
            user_id=str(current_user.id),
            doc_type=doc_type
        )
        
        logger.info(f"Deleted {deleted_count} documents for user {current_user.id}")
        
        return None
        
    except Exception as e:
        logger.error(f"Document deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document deletion failed: {str(e)}"
        )
