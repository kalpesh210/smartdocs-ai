import math
import hashlib
import logging
from typing import List
import numpy as np
from app.core.config import settings

logger = logging.getLogger("smartdocs.embedding")

class EmbeddingService:
    """
    Embedding service generating normalized vectors.
    Supports:
    - Google AI Studio (text-embedding-004, 768 dimensions) via google-genai SDK
    - OpenAI (text-embedding-3-small, 1536 dimensions) via openai SDK
    - Intelligent deterministic offline fallback for local development & testing.
    """

    def __init__(self):
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self._gemini_client = None
        self._openai_client = None

        # 1. Initialize Google GenAI client if Gemini API key is configured
        if self.gemini_api_key and not self.gemini_api_key.startswith("your_") and not self.gemini_api_key.startswith("mock"):
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.gemini_api_key)
                logger.info(f"Initialized Google GenAI Embedding Service with model {self.model} ({self.dimension}d)")
            except Exception as e:
                logger.warning(f"Failed to initialize Google GenAI client: {e}. Fallback embedding enabled.")

        # 2. Initialize OpenAI client if Gemini is not used and OpenAI key is provided
        if not self._gemini_client and self.openai_api_key and not self.openai_api_key.startswith("your_") and not self.openai_api_key.startswith("mock"):
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_api_key)
                logger.info(f"Initialized OpenAI Embedding Service with model {self.model} ({self.dimension}d)")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Fallback embedding enabled.")

    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """
        Deterministic, semantic-biased unit vector generator matching configured dimension.
        Uses character n-grams and token hashing with Gaussian projection to simulate
        semantic density, normalized to unit L2 norm so cosine similarity works accurately.
        """
        if not text:
            vec = np.zeros(self.dimension)
            vec[0] = 1.0
            return vec.tolist()

        # Seed random generator deterministically using SHA-256 of text n-grams
        tokens = text.lower().split()
        vector = np.zeros(self.dimension, dtype=np.float32)

        for i, token in enumerate(tokens):
            token_hash = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
            np.random.seed(token_hash % (2**32 - 1))
            # Weight early tokens slightly higher (document title/intro importance)
            weight = 1.0 / math.sqrt(i + 1)
            token_projection = np.random.normal(0, 1.0, self.dimension)
            vector += weight * token_projection

        # Also hash trigrams for word order capturing
        for i in range(len(text) - 2):
            tri = text[i:i+3].encode('utf-8')
            thash = int(hashlib.sha256(tri).hexdigest()[:8], 16)
            idx = thash % self.dimension
            vector[idx] += 0.2

        # L2 Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        else:
            vector[0] = 1.0

        return vector.tolist()

    def get_embedding(self, text: str) -> List[float]:
        """Generates embedding for a single text string."""
        embeddings = self.get_embeddings([text])
        return embeddings[0]

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of text strings."""
        if not texts:
            return []

        # 1. Google GenAI client (Google AI Studio)
        if self._gemini_client:
            try:
                from google.genai import types
                sanitized = [t.replace("\r\n", " ").replace("\n", " ") for t in texts]
                config = types.EmbedContentConfig(output_dimensionality=self.dimension)
                embeddings = []
                for item in sanitized:
                    resp = self._gemini_client.models.embed_content(
                        model=self.model,
                        contents=item,
                        config=config
                    )
                    if hasattr(resp, "embeddings") and resp.embeddings:
                        embeddings.append(resp.embeddings[0].values)
                    elif hasattr(resp, "embedding") and resp.embedding:
                        embeddings.append(resp.embedding.values)
                if len(embeddings) == len(texts):
                    return embeddings
            except Exception as e:
                logger.error(f"Google GenAI embedding generation failed ({e}). Trying fallback.")

        # 2. OpenAI client fallback
        if self._openai_client:
            try:
                sanitized = [t.replace("\r\n", " ").replace("\n", " ") for t in texts]
                response = self._openai_client.embeddings.create(
                    input=sanitized,
                    model=self.model
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                logger.error(f"OpenAI embedding generation failed ({e}). Falling back to offline generator.")

        # 3. Offline fallback
        return [self._generate_fallback_embedding(t) for t in texts]

embedding_service = EmbeddingService()
