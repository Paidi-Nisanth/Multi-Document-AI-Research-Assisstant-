import json
import logging
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_db, get_current_user, get_current_workspace, require_role
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.models.document import Document
from app.api.v1.search import search_router_helper, SearchQuery
from app.services.prompt_builder import PromptBuilder
from app.services.budget_manager import BudgetManager
from app.services.citation_parser import CitationParser
from app.services.llm import LLMService
from app.services.memory_manager import MemoryManager
from app.services.comparison import MultiDocComparator
from app.services.semantic_cache import SemanticCacheService

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatMessageTurn(BaseModel):
    role: str  # user | assistant
    text: str


class ChatRequest(BaseModel):
    query: str
    search_mode: str = "rerank"  # rerank | hybrid | vector | keyword
    top_k: int = 5
    temperature: float = 0.2
    conversation_id: Optional[str] = None
    use_cache: bool = True
    history: Optional[List[ChatMessageTurn]] = []


class CitationObject(BaseModel):
    citation_id: int
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    filename: Optional[str] = None
    section: Optional[str] = None
    page_number: Optional[int] = None
    content: Optional[str] = None
    similarity_score: Optional[float] = None
    rerank_score: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    citations: List[CitationObject]
    sources_used: List[dict]
    summary_memory: Optional[str] = None
    provider: str
    cached: bool = False
    cache_similarity: Optional[float] = None


class CompareRequest(BaseModel):
    document_ids: Optional[List[str]] = None
    comparison_axes: Optional[List[str]] = None
    query: Optional[str] = "Compare these research papers across key technical axes"


async def fetch_workspace_documents_meta(db: AsyncSession, workspace_id: str) -> List[dict]:
    stmt = select(Document).options(selectinload(Document.chunks)).where(Document.workspace_id == workspace_id)
    res = await db.execute(stmt)
    docs = res.scalars().all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "file_type": d.file_type or "pdf",
            "total_chunks": len(d.chunks) if d.chunks else 0,
        }
        for d in docs
    ]


@router.post("/completions", response_model=ChatResponse)
async def chat_completions(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    query_text = req.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Conversation Persistence Setup
    conv = await MemoryManager.get_or_create_conversation(
        db=db,
        workspace_id=str(workspace.id),
        user_id=str(user.id),
        conversation_id=req.conversation_id,
        initial_query=query_text
    )

    await MemoryManager.persist_user_message(
        db=db,
        workspace_id=str(workspace.id),
        conversation_id=str(conv.id),
        content=query_text
    )

    # 2. Semantic Query Cache Check
    if req.use_cache:
        cached_hit = await SemanticCacheService.get_cached_response(
            db=db,
            workspace_id=str(workspace.id),
            query_text=query_text,
            threshold=0.95
        )
        if cached_hit:
            await MemoryManager.persist_assistant_message(
                db=db,
                workspace_id=str(workspace.id),
                conversation_id=str(conv.id),
                content=cached_hit["answer"],
                citations=cached_hit["citations"]
            )
            return ChatResponse(
                answer=cached_hit["answer"],
                conversation_id=str(conv.id),
                citations=[CitationObject(**c) for c in cached_hit.get("citations", [])],
                sources_used=[],
                summary_memory=conv.summary_memory,
                provider="semantic_cache",
                cached=True,
                cache_similarity=cached_hit.get("similarity", 1.0)
            )

    # 3. Retrieve sliding window + condensed long-term memory
    sliding_history, summary_memory = await MemoryManager.get_window_and_summary(
        db=db,
        conversation_id=str(conv.id),
        window_size=MemoryManager.DEFAULT_WINDOW_SIZE
    )

    # 4. Fetch Workspace Document Catalog (Macro Context)
    workspace_docs = await fetch_workspace_documents_meta(db, str(workspace.id))

    # 5. Retrieve Candidate Technical Chunks (Micro Context)
    search_results = await search_router_helper(
        mode=req.search_mode,
        query=query_text,
        top_k=req.top_k,
        db=db,
        workspace=workspace
    )

    # 6. Fit Sources under Context Budget
    raw_sources = [r.model_dump() for r in search_results]
    budget_mgr = BudgetManager(max_context_tokens=32000)
    fitted_sources = budget_mgr.fit_sources_under_budget(raw_sources)

    # 7. Build Unified Universal RAG Prompt with Memory
    sys_prompt, user_prompt, source_map = PromptBuilder.build_unified_rag_prompt(
        workspace_docs=workspace_docs,
        query=query_text,
        sources=fitted_sources,
        chat_history=sliding_history,
        summary_memory=summary_memory
    )

    # 8. Generate Response via LLM Engine
    llm_raw_text = await LLMService.generate_response(
        system_instruction=sys_prompt,
        user_prompt=user_prompt,
        temperature=req.temperature
    )

    # 9. Parse Citations
    clean_answer, citations = CitationParser.parse_citations(llm_raw_text, source_map)

    # 10. Persist Assistant Response in PostgreSQL
    await MemoryManager.persist_assistant_message(
        db=db,
        workspace_id=str(workspace.id),
        conversation_id=str(conv.id),
        content=clean_answer,
        citations=citations
    )

    # 11. Write to Semantic Cache
    if req.use_cache and not clean_answer.startswith("Error"):
        await SemanticCacheService.set_cached_response(
            db=db,
            workspace_id=str(workspace.id),
            query_text=query_text,
            answer=clean_answer,
            citations=citations
        )

    return ChatResponse(
        answer=clean_answer,
        conversation_id=str(conv.id),
        citations=[CitationObject(**c) for c in citations],
        sources_used=fitted_sources,
        summary_memory=summary_memory,
        provider=LLMService.get_provider(),
        cached=False,
        cache_similarity=None
    )


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    query_text = req.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Conversation Persistence & Memory
    conv = await MemoryManager.get_or_create_conversation(
        db=db,
        workspace_id=str(workspace.id),
        user_id=str(user.id),
        conversation_id=req.conversation_id,
        initial_query=query_text
    )

    await MemoryManager.persist_user_message(
        db=db,
        workspace_id=str(workspace.id),
        conversation_id=str(conv.id),
        content=query_text
    )

    # 2. Semantic Cache Check for Streaming
    if req.use_cache:
        cached_hit = await SemanticCacheService.get_cached_response(
            db=db,
            workspace_id=str(workspace.id),
            query_text=query_text,
            threshold=0.95
        )
        if cached_hit:
            await MemoryManager.persist_assistant_message(
                db=db,
                workspace_id=str(workspace.id),
                conversation_id=str(conv.id),
                content=cached_hit["answer"],
                citations=cached_hit["citations"]
            )

            async def cached_stream_gen():
                data_frame = json.dumps({"token": cached_hit["answer"]})
                yield f"data: {data_frame}\n\n"
                meta_payload = {
                    "conversation_id": str(conv.id),
                    "summary_memory": conv.summary_memory,
                    "citations": cached_hit.get("citations", []),
                    "sources_used": [],
                    "provider": "semantic_cache",
                    "cached": True,
                    "cache_similarity": cached_hit.get("similarity", 1.0)
                }
                yield f"data: [CITATION_DATA]{json.dumps(meta_payload)}\n\n"

            return StreamingResponse(
                cached_stream_gen(),
                media_type="text/event-stream",
                headers={"X-Conversation-Id": str(conv.id)}
            )

    sliding_history, summary_memory = await MemoryManager.get_window_and_summary(
        db=db,
        conversation_id=str(conv.id),
        window_size=MemoryManager.DEFAULT_WINDOW_SIZE
    )

    workspace_docs = await fetch_workspace_documents_meta(db, str(workspace.id))

    search_results = await search_router_helper(
        mode=req.search_mode,
        query=query_text,
        top_k=req.top_k,
        db=db,
        workspace=workspace
    )

    raw_sources = [r.model_dump() for r in search_results]
    budget_mgr = BudgetManager(max_context_tokens=32000)
    fitted_sources = budget_mgr.fit_sources_under_budget(raw_sources)

    sys_prompt, user_prompt, source_map = PromptBuilder.build_unified_rag_prompt(
        workspace_docs=workspace_docs,
        query=query_text,
        sources=fitted_sources,
        chat_history=sliding_history,
        summary_memory=summary_memory
    )

    async def sse_event_generator():
        collected_tokens = []

        async for sse_frame in LLMService.stream_response(
            system_instruction=sys_prompt,
            user_prompt=user_prompt,
            temperature=req.temperature
        ):
            try:
                line_data = sse_frame.replace("data: ", "").strip()
                if line_data:
                    tok_obj = json.loads(line_data)
                    collected_tokens.append(tok_obj.get("token", ""))
            except Exception:
                pass
            yield sse_frame

        full_text = "".join(collected_tokens)
        _, citations = CitationParser.parse_citations(full_text, source_map)

        # Persist assistant turn in DB
        try:
            await MemoryManager.persist_assistant_message(
                db=db,
                workspace_id=str(workspace.id),
                conversation_id=str(conv.id),
                content=full_text,
                citations=citations
            )
        except Exception as p_err:
            logger.error(f"Failed to persist assistant message: {p_err}")

        # Store in Semantic Cache
        if req.use_cache and full_text and not full_text.startswith("Error"):
            try:
                await SemanticCacheService.set_cached_response(
                    db=db,
                    workspace_id=str(workspace.id),
                    query_text=query_text,
                    answer=full_text,
                    citations=citations
                )
            except Exception as c_err:
                logger.debug(f"Cache write error: {c_err}")

        meta_payload = {
            "conversation_id": str(conv.id),
            "summary_memory": summary_memory,
            "citations": citations,
            "sources_used": fitted_sources,
            "provider": LLMService.get_provider(),
            "cached": False,
            "cache_similarity": None
        }
        yield f"data: [CITATION_DATA]{json.dumps(meta_payload)}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={"X-Conversation-Id": str(conv.id)}
    )


@router.post("/compare")
async def multi_doc_compare(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role([UserRole.ADMIN, UserRole.EDITOR])),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    logger.info(f"Initiating multi-document comparison for workspace {workspace.id}")
    comparison_report = await MultiDocComparator.compare_documents(
        db=db,
        workspace_id=str(workspace.id),
        document_ids=req.document_ids,
        comparison_axes=req.comparison_axes,
        query=req.query
    )
    return comparison_report
