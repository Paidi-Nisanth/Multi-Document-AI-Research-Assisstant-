import uuid
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.worker import celery_app
from app.config import settings
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.services.extractor import DocumentExtractor
from app.services.chunker import StructureAwareChunker
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

# Sync Engine for Celery tasks
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=5
)
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)


@celery_app.task(name="app.tasks.ingestion.process_document_task", bind=True, max_retries=3)
def process_document_task(self, document_id: str, workspace_id: str):
    logger.info(f"Starting ingestion task for document={document_id}, workspace={workspace_id}")
    db = SyncSessionLocal()
    
    try:
        str_doc_id = str(document_id)
        str_ws_id = str(workspace_id)

        # 1. Fetch document and update status to processing
        doc = db.query(Document).filter(
            Document.id == str_doc_id, Document.workspace_id == str_ws_id
        ).first()

        if not doc:
            logger.error(f"Document {document_id} not found in workspace {workspace_id}")
            return {"status": "error", "message": "Document not found"}

        doc.status = DocumentStatus.PROCESSING
        db.commit()

        # 2. Extract text and structural metadata
        logger.info(f"Extracting content from {doc.file_path} (type: {doc.file_type})")
        extracted_blocks = DocumentExtractor.extract(doc.file_path, doc.file_type)

        if not extracted_blocks:
            raise ValueError("No text could be extracted from document.")

        # 3. Structure-aware chunking
        logger.info(f"Chunking extracted blocks from {doc.filename}")
        chunker = StructureAwareChunker(target_tokens=600, overlap_tokens=100)
        chunk_outputs = chunker.chunk_blocks(extracted_blocks)

        # 4. Bulk insert chunks into DB
        logger.info(f"Persisting {len(chunk_outputs)} chunks into DB...")
        db_chunks = []
        for c in chunk_outputs:
            chunk_obj = Chunk(
                id=str(uuid.uuid4()),
                workspace_id=str_ws_id,
                document_id=str_doc_id,
                content=c.content,
                chunk_index=c.chunk_index,
                section=c.section,
                page_number=c.page_number,
                chunk_metadata=c.chunk_metadata,
            )
            db_chunks.append(chunk_obj)

        db.bulk_save_objects(db_chunks)
        db.commit()

        # Update status to CHUNKED
        doc.status = DocumentStatus.CHUNKED
        db.commit()

        # 5. Generate Vectors and Insert Embeddings
        logger.info(f"Generating dense vector embeddings for {len(db_chunks)} chunks...")
        chunk_texts = [c.content for c in db_chunks]
        vectors = EmbeddingService.generate_embeddings(chunk_texts)

        db_embeddings = []
        for idx, vec in enumerate(vectors):
            emb_obj = Embedding(
                id=str(uuid.uuid4()),
                workspace_id=str_ws_id,
                chunk_id=str(db_chunks[idx].id),
                embedding=vec
            )
            db_embeddings.append(emb_obj)

        db.bulk_save_objects(db_embeddings)

        # 6. Update document status to READY
        updated_metadata = dict(doc.doc_metadata or {})
        updated_metadata["chunk_count"] = len(chunk_outputs)
        updated_metadata["extracted_blocks_count"] = len(extracted_blocks)
        updated_metadata["embeddings_count"] = len(db_embeddings)
        
        doc.status = DocumentStatus.READY
        doc.doc_metadata = updated_metadata
        db.commit()

        logger.info(f"Successfully processed document {document_id}. Status: READY. Total chunks: {len(chunk_outputs)}")
        return {
            "status": "success",
            "document_id": document_id,
            "chunks_created": len(chunk_outputs),
            "embeddings_created": len(db_embeddings)
        }

    except Exception as exc:
        logger.exception(f"Error processing document {document_id}: {exc}")
        db.rollback()
        
        try:
            doc = db.query(Document).filter(Document.id == str(document_id)).first()
            if doc:
                doc.status = DocumentStatus.ERROR
                updated_metadata = dict(doc.doc_metadata or {})
                updated_metadata["error_message"] = str(exc)
                doc.doc_metadata = updated_metadata
                db.commit()
        except Exception as inner_exc:
            logger.error(f"Failed to update error status for doc {document_id}: {inner_exc}")

        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()
