import numpy as np
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1.deps import get_db, get_current_workspace
from app.models.workspace import Workspace
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.embedding import Embedding
from app.services.embedding import EmbeddingService
from app.services.reranker import CrossEncoderReranker

router = APIRouter()


class SearchQuery(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    section: Optional[str]
    page_number: Optional[int]
    content: str
    similarity_score: float
    rank: Optional[int] = None
    rerank_score: Optional[float] = None
    metadata: dict = {}


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    a = np.array(v1, dtype=float)
    b = np.array(v2, dtype=float)
    norm = (np.linalg.norm(a) * np.linalg.norm(b))
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / norm)


def is_bibliography_chunk(section: Optional[str], content: str, query: str) -> bool:
    query_lower = query.lower()
    if "reference" in query_lower or "bibliography" in query_lower or "author" in query_lower:
        return False
    sec_lower = (section or "").lower()
    if any(k in sec_lower for k in ["reference", "bibliography", "works cited", "acknowledgement"]):
        return True
    content_lower = content.lower()
    if content_lower.count("proceedings of") >= 2 or content_lower.count("vol.") >= 2 or content_lower.count("arxiv:") >= 2:
        return True
    return False


@router.post("/vector", response_model=List[SearchResult])
async def vector_search(
    query_in: SearchQuery,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    query_text = query_in.query.strip()
    if not query_text:
        return []

    # 1. Generate query embedding
    query_vec = EmbeddingService.generate_query_embedding(query_text)

    # 2. Query chunks & embeddings for workspace
    stmt = (
        select(Chunk, Document, Embedding)
        .join(Document, Chunk.document_id == Document.id)
        .outerjoin(Embedding, Chunk.id == Embedding.chunk_id)
        .where(Chunk.workspace_id == str(workspace.id))
    )
    result = await db.execute(stmt)
    rows = result.all()

    results: List[SearchResult] = []
    for chunk, doc, emb in rows:
        score = 0.0
        if emb and emb.embedding:
            if isinstance(emb.embedding, list):
                score = cosine_similarity(query_vec, emb.embedding)
            elif hasattr(emb.embedding, "tolist"):
                score = cosine_similarity(query_vec, emb.embedding.tolist())
            else:
                try:
                    vec_list = [float(x) for x in str(emb.embedding).strip("[]").split(",")]
                    score = cosine_similarity(query_vec, vec_list)
                except Exception:
                    score = 0.5
        else:
            content_lower = chunk.content.lower()
            query_words = [w for w in query_text.lower().split() if len(w) >= 1]
            matches = sum(1 for w in query_words if w in content_lower)
            score = float(matches / max(1, len(query_words))) * 0.5

        # Penalize bibliography/reference chunks so technical body content is prioritized
        if is_bibliography_chunk(chunk.section, chunk.content, query_text):
            score *= 0.2

        results.append(
            SearchResult(
                chunk_id=str(chunk.id),
                document_id=str(doc.id),
                filename=doc.filename,
                section=chunk.section or "Section Overview",
                page_number=chunk.page_number,
                content=chunk.content,
                similarity_score=round(score, 4),
                metadata=chunk.chunk_metadata or {}
            )
        )

    # Sort descending by similarity score
    results.sort(key=lambda x: x.similarity_score, reverse=True)
    for idx, r in enumerate(results[: query_in.top_k]):
        r.rank = idx + 1

    return results[: query_in.top_k]


@router.post("/keyword", response_model=List[SearchResult])
async def keyword_search(
    query_in: SearchQuery,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    query_text = query_in.query.strip()
    if not query_text:
        return []

    stmt = (
        select(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.workspace_id == str(workspace.id))
    )
    result = await db.execute(stmt)
    rows = result.all()

    query_lower = query_text.lower()
    query_tokens = [t.lower() for t in query_text.split() if len(t) >= 1]
    results: List[SearchResult] = []

    for chunk, doc in rows:
        content_lower = chunk.content.lower()
        
        exact_phrase_match = query_lower in content_lower
        matches = sum(1 for t in query_tokens if t in content_lower)

        if exact_phrase_match or matches > 0:
            token_ratio = float(matches / max(1, len(query_tokens)))
            score = token_ratio + (1.0 if exact_phrase_match else 0.0)

            # Penalize bibliography/reference chunks
            if is_bibliography_chunk(chunk.section, chunk.content, query_text):
                score *= 0.2
            
            results.append(
                SearchResult(
                    chunk_id=str(chunk.id),
                    document_id=str(doc.id),
                    filename=doc.filename,
                    section=chunk.section or "Section Overview",
                    page_number=chunk.page_number,
                    content=chunk.content,
                    similarity_score=round(score, 4),
                    metadata=chunk.chunk_metadata or {}
                )
            )

    results.sort(key=lambda x: x.similarity_score, reverse=True)
    for idx, r in enumerate(results[: query_in.top_k]):
        r.rank = idx + 1

    return results[: query_in.top_k]


@router.post("/hybrid", response_model=List[SearchResult])
async def hybrid_search(
    query_in: SearchQuery,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    vec_query = SearchQuery(query=query_in.query, top_k=20)
    kw_query = SearchQuery(query=query_in.query, top_k=20)

    vec_results = await vector_search(vec_query, db, workspace)
    kw_results = await keyword_search(kw_query, db, workspace)

    k_constant = 60
    rrf_scores = {}
    chunk_map = {}

    for rank, res in enumerate(vec_results):
        cid = res.chunk_id
        chunk_map[cid] = res
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k_constant + (rank + 1)))

    for rank, res in enumerate(kw_results):
        cid = res.chunk_id
        chunk_map[cid] = res
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k_constant + (rank + 1)))

    sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    hybrid_results = []
    for rank, cid in enumerate(sorted_chunk_ids[: query_in.top_k]):
        item = chunk_map[cid]
        item.similarity_score = round(rrf_scores[cid], 6)
        item.rank = rank + 1
        hybrid_results.append(item)

    return hybrid_results


@router.post("/rerank", response_model=List[SearchResult])
async def rerank_search(
    query_in: SearchQuery,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    hybrid_candidates = await hybrid_search(SearchQuery(query=query_in.query, top_k=20), db, workspace)

    if not hybrid_candidates:
        return []

    cand_dicts = [item.model_dump() for item in hybrid_candidates]
    reranked = CrossEncoderReranker.rerank(query_in.query, cand_dicts, top_n=query_in.top_k)

    final_results = []
    for idx, r in enumerate(reranked):
        res_obj = SearchResult(**r)
        res_obj.rank = idx + 1
        final_results.append(res_obj)

    return final_results


def filter_diverse_chunks(results: List[SearchResult], top_k: int) -> List[SearchResult]:
    """
    Deduplicates near-identical chunks from the same document section so cited sources
    span distinct pages and sections rather than repeating the same paragraph.
    """
    diverse: List[SearchResult] = []
    seen_keys = set()

    for r in results:
        # Group key by document_id and first 80 characters of content
        content_key = f"{r.document_id}_{r.content[:80].strip()}"
        if content_key in seen_keys:
            continue
        seen_keys.add(content_key)
        diverse.append(r)
        if len(diverse) >= top_k:
            break

    for idx, d in enumerate(diverse, 1):
        d.rank = idx

    return diverse


async def search_router_helper(
    mode: str,
    query: str,
    top_k: int,
    db: AsyncSession,
    workspace: Workspace
) -> List[SearchResult]:
    sq = SearchQuery(query=query, top_k=top_k * 2)
    mode_lower = mode.lower()
    if mode_lower == "vector":
        raw_res = await vector_search(sq, db, workspace)
    elif mode_lower == "keyword":
        raw_res = await keyword_search(sq, db, workspace)
    elif mode_lower == "hybrid":
        raw_res = await hybrid_search(sq, db, workspace)
    else:
        raw_res = await rerank_search(sq, db, workspace)

    return filter_diverse_chunks(raw_res, top_k)
