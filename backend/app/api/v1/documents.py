import os
import uuid
import logging
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1.deps import get_db, get_current_workspace, get_current_user, require_role
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.services.extractor import DocumentExtractor
from app.services.chunker import StructureAwareChunker
from app.services.embedding import EmbeddingService
from app.services.doc_summarizer import DocumentSummarizer

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class SummarizeRequest(BaseModel):
    force_refresh: bool = False


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(require_role([UserRole.ADMIN, UserRole.EDITOR])),
) -> Any:
    # 1. Validate file format
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ["pdf", "docx", "txt", "md"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '.{ext}'. Supported formats: PDF, DOCX, TXT, MD."
        )

    # 2. Save file to disk
    workspace_upload_dir = os.path.join(UPLOAD_DIR, str(workspace.id))
    os.makedirs(workspace_upload_dir, exist_ok=True)

    doc_id = str(uuid.uuid4())
    filename = f"{doc_id}_{file.filename}"
    file_path = os.path.join(workspace_upload_dir, filename)

    contents = await file.read()
    file_size = len(contents)

    with open(file_path, "wb") as f:
        f.write(contents)

    # 3. Create Document DB record
    document = Document(
        id=doc_id,
        workspace_id=str(workspace.id),
        filename=file.filename,
        file_path=file_path,
        file_type=ext,
        file_size=file_size,
        status=DocumentStatus.PROCESSING,
        doc_metadata={"uploaded_by": str(user.id)},
    )
    db.add(document)
    await db.commit()

    # 4. Instant Ingestion: Extract, Chunk, and Embed
    try:
        blocks = DocumentExtractor.extract(file_path, ext)
        if not blocks:
            raise ValueError("No text could be extracted from file.")

        chunker = StructureAwareChunker(target_tokens=600, overlap_tokens=100)
        chunk_outputs = chunker.chunk_blocks(blocks)

        db_chunks = []
        for c in chunk_outputs:
            chunk_obj = Chunk(
                id=str(uuid.uuid4()),
                workspace_id=str(workspace.id),
                document_id=str(document.id),
                content=c.content,
                chunk_index=c.chunk_index,
                section=c.section,
                page_number=c.page_number,
                chunk_metadata=c.chunk_metadata,
            )
            db.add(chunk_obj)
            db_chunks.append(chunk_obj)

        await db.flush()

        # Generate Embeddings
        chunk_texts = [c.content for c in db_chunks]
        vectors = EmbeddingService.generate_embeddings(chunk_texts)

        for idx, vec in enumerate(vectors):
            emb_obj = Embedding(
                id=str(uuid.uuid4()),
                workspace_id=str(workspace.id),
                chunk_id=str(db_chunks[idx].id),
                embedding=vec
            )
            db.add(emb_obj)

        meta = dict(document.doc_metadata or {})
        meta["chunk_count"] = len(chunk_outputs)
        meta["extracted_blocks_count"] = len(blocks)
        meta["embeddings_count"] = len(vectors)
        document.status = DocumentStatus.READY
        document.doc_metadata = meta
        await db.commit()
        await db.refresh(document)

        logger.info(f"Instant ingestion complete for doc {document.id}. Created {len(chunk_outputs)} chunks and {len(vectors)} embeddings.")

    except Exception as proc_exc:
        logger.exception(f"Ingestion error for doc {document.id}: {proc_exc}")
        document.status = DocumentStatus.ERROR
        meta = dict(document.doc_metadata or {})
        meta["error_message"] = str(proc_exc)
        document.doc_metadata = meta
        await db.commit()
        await db.refresh(document)

    return {
        "id": str(document.id),
        "workspace_id": str(document.workspace_id),
        "filename": document.filename,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "status": document.status,
        "summary": document.summary,
        "doc_metadata": document.doc_metadata,
        "created_at": document.created_at,
    }


@router.get("/", response_model=List[dict])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
) -> Any:
    stmt = (
        select(Document)
        .where(Document.workspace_id == str(workspace.id))
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return [
        {
            "id": str(doc.id),
            "workspace_id": str(doc.workspace_id),
            "filename": doc.filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "status": doc.status,
            "summary": doc.summary,
            "doc_metadata": doc.doc_metadata,
            "created_at": doc.created_at,
        }
        for doc in docs
    ]


@router.get("/{document_id}")
async def get_document_details(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
) -> Any:
    stmt = select(Document).where(
        Document.id == str(document_id), Document.workspace_id == str(workspace.id)
    )
    result = await db.execute(stmt)
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_stmt = (
        select(Chunk)
        .where(Chunk.document_id == str(doc.id))
        .order_by(Chunk.chunk_index.asc())
    )
    chunk_res = await db.execute(chunk_stmt)
    chunks = chunk_res.scalars().all()

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "status": doc.status,
        "summary": doc.summary,
        "doc_metadata": doc.doc_metadata,
        "chunks": [
            {
                "id": str(c.id),
                "chunk_index": c.chunk_index,
                "section": c.section,
                "page_number": c.page_number,
                "content": c.content,
                "chunk_metadata": c.chunk_metadata,
            }
            for c in chunks
        ],
    }


@router.post("/{document_id}/summarize")
async def summarize_document_endpoint(
    document_id: str,
    payload: Optional[SummarizeRequest] = None,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(require_role([UserRole.ADMIN, UserRole.EDITOR])),
) -> Any:
    """
    Executes hierarchical Map-Reduce summarization over document chunks and caches result on document.summary.
    """
    force_refresh = payload.force_refresh if payload else False
    try:
        summary_obj = await DocumentSummarizer.summarize_document(
            db=db,
            document_id=document_id,
            workspace_id=str(workspace.id),
            force_refresh=force_refresh
        )
        return summary_obj
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Error summarizing document {document_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Summarization error: {str(exc)}")


@router.get("/{document_id}/summary")
async def get_document_summary(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
) -> Any:
    stmt = select(Document).where(
        Document.id == str(document_id), Document.workspace_id == str(workspace.id)
    )
    result = await db.execute(stmt)
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.summary:
        raise HTTPException(status_code=404, detail="Summary not yet generated for this document.")

    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "cached": True,
        "summary": doc.summary
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(require_role([UserRole.ADMIN, UserRole.EDITOR])),
) -> Any:
    stmt = select(Document).where(
        Document.id == str(document_id), Document.workspace_id == str(workspace.id)
    )
    result = await db.execute(stmt)
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file {doc.file_path}: {e}")

    await db.delete(doc)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
