"""
Vector embedding service — OpenAI embeddings with caching and batch support.
Used by hybrid search and entity similarity queries.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import List, Optional

import openai
from fastapi import Depends

from app.core.config import settings

logger = logging.getLogger("tada.vector_service")

# Simple in-process LRU cache (upgrade to Redis for multi-process deployments)
_cache: dict[str, List[float]] = {}
_MAX_CACHE_SIZE = 10_000


class VectorService:
    """
    Wraps the OpenAI Embeddings API with:
    - Async batch embedding (up to 2048 texts per call)
    - SHA-256-keyed in-process cache
    - Automatic retry on rate-limit (429) via openai backoff
    """

    MODEL = "text-embedding-3-small"  # 1536 dimensions
    DIMENSIONS = 1536

    def __init__(self) -> None:
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # ─── Public API ──────────────────────────────────────────────────────────
    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query string (cached)."""
        return (await self.embed_texts([text]))[0]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts.
        Cache hits are served immediately; misses are batched to OpenAI.
        """
        if not texts:
            return []

        results: dict[int, List[float]] = {}
        uncached: list[tuple[int, str]] = []  # (original_index, text)

        for i, t in enumerate(texts):
            key = _cache_key(t)
            if key in _cache:
                results[i] = _cache[key]
            else:
                uncached.append((i, t))

        if uncached:
            fresh = await self._embed_batch([t for _, t in uncached])
            for (orig_idx, t), embedding in zip(uncached, fresh):
                key = _cache_key(t)
                _maybe_store_cache(key, embedding)
                results[orig_idx] = embedding

        return [results[i] for i in range(len(texts))]

    async def embed_document(self, content: str, title: Optional[str] = None) -> List[float]:
        """
        Embed a document for indexing.
        Prepend title for richer representation when available.
        """
        text = f"{title}: {content}" if title else content
        # Truncate to ~8000 tokens (approx 32 000 chars) to stay within limits
        text = text[:32_000]
        return await self.embed_query(text)

    # ─── pgvector helpers ─────────────────────────────────────────────────────
    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Pure-Python cosine similarity (for in-memory comparisons)."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ─── Internals ────────────────────────────────────────────────────────────
    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Call OpenAI API in chunks of 2048 (API limit)."""
        CHUNK = 2048
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), CHUNK):
            chunk = texts[i : i + CHUNK]
            try:
                response = await self._client.embeddings.create(
                    input=chunk,
                    model=self.MODEL,
                    dimensions=self.DIMENSIONS,
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                logger.debug("Embedded %d texts (batch %d)", len(chunk), i // CHUNK)
            except openai.RateLimitError:
                logger.warning("Rate limit hit — backing off 5s before retry")
                await asyncio.sleep(5)
                response = await self._client.embeddings.create(
                    input=chunk,
                    model=self.MODEL,
                    dimensions=self.DIMENSIONS,
                )
                all_embeddings.extend([item.embedding for item in response.data])
            except Exception as exc:
                logger.error("Embedding API error: %s", exc)
                raise

        return all_embeddings


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _maybe_store_cache(key: str, embedding: List[float]) -> None:
    if len(_cache) >= _MAX_CACHE_SIZE:
        # Evict oldest key (dict insertion order, Python 3.7+)
        evict = next(iter(_cache))
        del _cache[evict]
    _cache[key] = embedding


# FastAPI dependency
async def get_vector_service() -> VectorService:
    return VectorService()
