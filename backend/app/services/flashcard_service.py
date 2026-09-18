import re
import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.chunk import Chunk
from app.models.flashcard import Flashcard
from app.services.llm import LLMService

logger = logging.getLogger(__name__)


class FlashcardService:
    @staticmethod
    async def generate_flashcards_for_document(
        db: AsyncSession,
        document_id: str,
        workspace_id: str,
        num_cards: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Generates technical study flashcards from document chunks using structured JSON output.
        """
        stmt = (
            select(Document)
            .options(selectinload(Document.chunks))
            .where(
                Document.id == str(document_id),
                Document.workspace_id == str(workspace_id)
            )
        )
        res = await db.execute(stmt)
        doc = res.scalars().first()
        if not doc:
            raise ValueError("Document not found in the current workspace.")

        chunks = sorted(doc.chunks or [], key=lambda c: c.chunk_index)
        if not chunks:
            raise ValueError("Document has no text chunks to generate flashcards from.")

        # Filter out pure bibliography chunks
        valid_chunks = [
            c for c in chunks
            if not any(k in (c.section or "").lower() for k in ["reference", "bibliography", "works cited"])
        ]
        if not valid_chunks:
            valid_chunks = chunks

        # Pick up to 5 diverse chunks across the paper
        step = max(1, len(valid_chunks) // 5)
        sample_chunks = valid_chunks[::step][:5]

        chunks_context = []
        for c in sample_chunks:
            chunks_context.append(
                f"<chunk id=\"{c.id}\" page=\"{c.page_number}\" section=\"{c.section or 'General'}\">\n"
                f"{c.content[:1200]}\n"
                f"</chunk>"
            )
        chunks_xml = "\n\n".join(chunks_context)

        sys_instruction = (
            "You are an expert academic tutor and flashcard engineer specializing in AI and systems papers.\n"
            "Generate high-yield, technically rigorous question-answer study flashcards strictly grounded in the provided document chunks.\n"
            "Format your entire response as a valid JSON array of objects with keys: 'chunk_id', 'question', 'answer'.\n"
            "Do NOT include markdown formatting, backticks, or any commentary outside the JSON array."
        )

        user_prompt = (
            f"Paper: {doc.filename}\n\n"
            f"Document Chunks:\n{chunks_xml}\n\n"
            f"Generate exactly {num_cards} distinct question-answer flashcard pairs targeting key architectural choices, "
            f"mathematical formulations, quantization scales, benchmarks, or limitations.\n"
            f"Example format:\n"
            f'[\n  {{\n    "chunk_id": "{sample_chunks[0].id}",\n    "question": "What is the primary trade-off of...",\n    "answer": "..."\n  }}\n]'
        )

        raw_llm_output = await LLMService.generate_response(
            system_instruction=sys_instruction,
            user_prompt=user_prompt,
            temperature=0.2
        )

        # Clean code blocks or markdown wrappers
        clean_json_str = raw_llm_output.strip()
        if clean_json_str.startswith("```json"):
            clean_json_str = clean_json_str[7:]
        elif clean_json_str.startswith("```"):
            clean_json_str = clean_json_str[3:]
        if clean_json_str.endswith("```"):
            clean_json_str = clean_json_str[:-3]
        clean_json_str = clean_json_str.strip()

        # Parse JSON
        parsed_cards = []
        try:
            parsed_cards = json.loads(clean_json_str)
        except Exception as parse_err:
            logger.warning(f"Direct JSON parse failed: {parse_err}. Attempting regex extraction.")
            match = re.search(r"\[\s*\{.*\}\s*\]", clean_json_str, re.DOTALL)
            if match:
                try:
                    parsed_cards = json.loads(match.group(0))
                except Exception:
                    pass

        if not parsed_cards:
            logger.error("Could not parse structured flashcards from LLM response.")
            raise ValueError("Failed to generate structured flashcard JSON from document.")

        # Persist to database
        created_records = []
        for item in parsed_cards:
            q = item.get("question", "").strip()
            a = item.get("answer", "").strip()
            cid = item.get("chunk_id", sample_chunks[0].id)
            if q and a:
                fc = Flashcard(
                    id=str(uuid.uuid4()),
                    workspace_id=str(workspace_id),
                    source_chunk_id=str(cid) if cid else None,
                    question=q,
                    answer=a,
                )
                db.add(fc)
                created_records.append({
                    "id": str(fc.id),
                    "document_id": str(doc.id),
                    "filename": doc.filename,
                    "source_chunk_id": str(cid),
                    "question": q,
                    "answer": a,
                })

        await db.commit()
        logger.info(f"Persisted {len(created_records)} flashcards for doc '{doc.filename}' ({doc.id})")
        return created_records

    @staticmethod
    async def list_flashcards(
        db: AsyncSession,
        workspace_id: str,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(Flashcard, Chunk, Document)
            .outerjoin(Chunk, Flashcard.source_chunk_id == Chunk.id)
            .outerjoin(Document, Chunk.document_id == Document.id)
            .where(Flashcard.workspace_id == str(workspace_id))
            .order_by(desc(Flashcard.created_at))
        )
        if document_id:
            stmt = stmt.where(Chunk.document_id == str(document_id))

        res = await db.execute(stmt)
        rows = res.all()

        results = []
        for fc, chunk, doc in rows:
            results.append({
                "id": str(fc.id),
                "workspace_id": str(fc.workspace_id),
                "source_chunk_id": str(fc.source_chunk_id) if fc.source_chunk_id else None,
                "document_id": str(doc.id) if doc else None,
                "filename": doc.filename if doc else "Workspace Document",
                "section": chunk.section if chunk else None,
                "page_number": chunk.page_number if chunk else None,
                "question": fc.question,
                "answer": fc.answer,
                "created_at": fc.created_at,
            })
        return results

    @staticmethod
    async def delete_flashcard(
        db: AsyncSession,
        workspace_id: str,
        flashcard_id: str
    ) -> bool:
        stmt = select(Flashcard).where(
            Flashcard.id == str(flashcard_id),
            Flashcard.workspace_id == str(workspace_id)
        )
        res = await db.execute(stmt)
        fc = res.scalars().first()
        if not fc:
            return False
        await db.delete(fc)
        await db.commit()
        return True
