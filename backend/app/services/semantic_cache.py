import os
import json
import uuid
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.query_cache import QueryCache
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

# Try to connect to Redis
try:
    import redis.asyncio as aioredis
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    redis_client = aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/0", decode_responses=True)
except Exception as redis_init_err:
    logger.warning(f"Redis initialization warning: {redis_init_err}")
    redis_client = None


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    a = np.array(v1, dtype=float)
    b = np.array(v2, dtype=float)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / norm)


class SemanticCacheService:
    SIMILARITY_THRESHOLD = 0.95
    DEFAULT_TTL_HOURS = 24

    @staticmethod
    def _get_exact_cache_key(workspace_id: str, query_text: str) -> str:
        q_hash = hashlib.md5(query_text.strip().lower().encode("utf-8")).hexdigest()
        return f"semcache:{workspace_id}:{q_hash}"

    @staticmethod
    async def get_cached_response(
        db: AsyncSession,
        workspace_id: str,
        query_text: str,
        threshold: float = SIMILARITY_THRESHOLD
    ) -> Optional[Dict[str, Any]]:
        """
        Checks for cached responses:
        1. Exact Match via Redis (O(1)).
        2. Semantic Similarity Match via pgvector query_cache table (threshold >= 0.95).
        """
        clean_query = query_text.strip()
        if not clean_query:
            return None

        # Tier 1: Exact Redis Match
        if redis_client:
            try:
                exact_key = SemanticCacheService._get_exact_cache_key(workspace_id, clean_query)
                exact_val = await redis_client.get(exact_key)
                if exact_val:
                    data = json.loads(exact_val)
                    logger.info(f"⚡ Exact Redis Cache Hit for query: '{clean_query[:50]}'")
                    return {
                        "cached": True,
                        "cache_type": "exact_redis",
                        "similarity": 1.0,
                        "answer": data.get("answer", ""),
                        "citations": data.get("citations", []),
                        "matched_query": clean_query
                    }
            except Exception as e:
                logger.debug(f"Redis read error: {e}")

        # Tier 2: Semantic Vector Similarity Match
        try:
            query_vec = EmbeddingService.generate_query_embedding(clean_query)
            now_utc = datetime.now(timezone.utc)

            stmt = select(QueryCache).where(
                QueryCache.workspace_id == str(workspace_id),
                (QueryCache.ttl_timestamp.is_(None) | (QueryCache.ttl_timestamp > now_utc))
            )
            res = await db.execute(stmt)
            cached_entries = res.scalars().all()

            best_sim = 0.0
            best_entry = None

            for entry in cached_entries:
                entry_emb = entry.query_embedding
                if isinstance(entry_emb, list):
                    emb_list = entry_emb
                elif hasattr(entry_emb, "tolist"):
                    emb_list = entry_emb.tolist()
                else:
                    try:
                        emb_list = [float(x) for x in str(entry_emb).strip("[]").split(",")]
                    except Exception:
                        continue

                sim = cosine_similarity(query_vec, emb_list)
                if sim > best_sim:
                    best_sim = sim
                    best_entry = entry

            if best_sim >= threshold and best_entry:
                logger.info(f"⚡ Semantic Cache Hit! (Similarity {best_sim:.4f} >= {threshold}) for '{clean_query[:40]}'")
                return {
                    "cached": True,
                    "cache_type": "semantic_vector",
                    "similarity": round(best_sim, 4),
                    "matched_query": best_entry.query_text,
                    "answer": best_entry.response_text,
                    "citations": best_entry.citations or []
                }

        except Exception as vec_err:
            logger.error(f"Semantic cache lookup error: {vec_err}")

        return None

    @staticmethod
    async def set_cached_response(
        db: AsyncSession,
        workspace_id: str,
        query_text: str,
        answer: str,
        citations: List[Any],
        ttl_hours: int = DEFAULT_TTL_HOURS
    ) -> None:
        """
        Stores query + response pair in both Redis and PostgreSQL query_cache table.
        """
        clean_query = query_text.strip()
        if not clean_query or not answer:
            return

        ttl_delta = timedelta(hours=ttl_hours)
        ttl_timestamp = datetime.now(timezone.utc) + ttl_delta

        # 1. Store in Redis
        if redis_client:
            try:
                exact_key = SemanticCacheService._get_exact_cache_key(workspace_id, clean_query)
                payload = json.dumps({"answer": answer, "citations": citations})
                await redis_client.set(exact_key, payload, ex=int(ttl_delta.total_seconds()))
            except Exception as e:
                logger.debug(f"Redis write error: {e}")

        # 2. Store in PostgreSQL query_cache
        try:
            query_vec = EmbeddingService.generate_query_embedding(clean_query)
            cache_record = QueryCache(
                id=str(uuid.uuid4()),
                workspace_id=str(workspace_id),
                query_text=clean_query,
                query_embedding=query_vec,
                response_text=answer,
                citations=citations,
                ttl_timestamp=ttl_timestamp
            )
            db.add(cache_record)
            await db.commit()
            logger.info(f"Stored query in semantic cache: '{clean_query[:50]}'")
        except Exception as db_err:
            logger.error(f"Failed to persist query cache record: {db_err}")
