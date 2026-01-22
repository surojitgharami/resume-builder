# app/services/embeddings.py
import logging
from typing import List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating text embeddings."""
    
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            Exception: If embedding generation fails
        """
        if self.provider == "openai":
            return await self._openai_embed(text)
        elif self.provider == "cohere":
            return await self._cohere_embed(text)
        elif self.provider == "local":
            return await self._local_embed(text)
        else:
            raise Exception(f"Unsupported embedding provider: {self.provider}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    async def _openai_embed(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        if not settings.OPENAI_API_KEY:
            raise Exception("OpenAI API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "input": text
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data['data'][0]['embedding']
                
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise Exception(f"OpenAI embedding failed: {str(e)}")
    
    async def _cohere_embed(self, text: str) -> List[float]:
        """Generate embedding using Cohere API."""
        if not settings.COHERE_API_KEY:
            raise Exception("Cohere API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cohere.ai/v1/embed",
                    headers={
                        "Authorization": f"Bearer {settings.COHERE_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "texts": [text]
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data['embeddings'][0]
                
        except Exception as e:
            logger.error(f"Cohere embedding failed: {e}")
            raise Exception(f"Cohere embedding failed: {str(e)}")
    
    async def _local_embed(self, text: str) -> List[float]:
        """Generate embedding using local model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            # Load model (consider caching this)
            model = SentenceTransformer(self.model)
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            raise Exception(f"Local embedding failed: {str(e)}")


# Global embeddings service instance
embeddings_service = EmbeddingsService()


def get_embeddings_service() -> EmbeddingsService:
    """Dependency to get embeddings service instance."""
    return embeddings_service
