import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.chunk import Chunk
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

DEFAULT_COMPARISON_AXES = [
    "Core Architecture & Methodology",
    "Precision & Numeric Formats",
    "Accuracy & Perplexity Impact",
    "Hardware Overhead & Latency",
    "Primary Limitations & Scope"
]


class MultiDocComparator:
    @staticmethod
    async def _map_document(
        doc: Document,
        chunks: List[Chunk],
        axes: List[str],
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Map Phase: Extracts structured technical notes for a single document along the requested axes.
        """
        chunks_text = "\n\n".join([
            f"[Page {c.page_number} - Section: {c.section or 'General'}]\n{c.content[:1500]}"
            for c in chunks[:6]
        ])

        axes_bullet_list = "\n".join([f"- {axis}" for axis in axes])

        system_instruction = (
            "You are a specialized academic research reader. Your job is to extract technical details from a research paper "
            "strictly across specified technical axes. Be concise, precise, and ground your notes directly in the provided text."
        )

        user_prompt = (
            f"Research Document: {doc.filename}\n\n"
            f"Extracted Paper Content:\n{chunks_text}\n\n"
            f"Target Technical Axes to Extract:\n{axes_bullet_list}\n\n"
            f"Focus Query: {query or 'General comparative extraction'}\n\n"
            "Provide structured technical notes for each axis for this specific paper."
        )

        try:
            summary = await LLMService.generate_response(
                system_instruction=system_instruction,
                user_prompt=user_prompt,
                temperature=0.2
            )
        except Exception as exc:
            logger.error(f"Error in Map phase for {doc.filename}: {exc}")
            summary = f"Could not extract summary for {doc.filename} due to an error: {exc}"

        return {
            "document_id": str(doc.id),
            "filename": doc.filename,
            "file_type": doc.file_type,
            "axes_summary": summary
        }

    @staticmethod
    async def compare_documents(
        db: AsyncSession,
        workspace_id: str,
        document_ids: Optional[List[str]] = None,
        comparison_axes: Optional[List[str]] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parallel Map-Reduce Multi-Document Comparison:
        1. Identifies documents to compare.
        2. In parallel, maps each document to structured notes along the comparison axes.
        3. Reduces all mapped summaries into a unified comparison table and trade-off analysis.
        """
        axes = comparison_axes or DEFAULT_COMPARISON_AXES

        # 1. Fetch target documents
        stmt = (
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.workspace_id == str(workspace_id))
        )
        if document_ids and len(document_ids) > 0:
            stmt = stmt.where(Document.id.in_([str(d) for d in document_ids]))

        res = await db.execute(stmt)
        docs = res.scalars().all()

        if len(docs) < 2:
            # Fallback: fetch all available documents in workspace if fewer than 2 matched
            all_stmt = select(Document).options(selectinload(Document.chunks)).where(Document.workspace_id == str(workspace_id))
            all_res = await db.execute(all_stmt)
            docs = all_res.scalars().all()

        if len(docs) < 2:
            return {
                "error": "At least 2 documents are required in the workspace to perform a multi-document comparison.",
                "documents_compared": [d.filename for d in docs],
                "comparison_table": "",
                "executive_summary": "Insufficient documents available for comparison."
            }

        # 2. Parallel Map Phase
        map_tasks = []
        for d in docs:
            chunks = sorted(d.chunks or [], key=lambda c: c.chunk_index)
            map_tasks.append(
                MultiDocComparator._map_document(
                    doc=d,
                    chunks=chunks,
                    axes=axes,
                    query=query
                )
            )

        map_results = await asyncio.gather(*map_tasks)

        # 3. Reduce Phase: Single LLM Synthesis
        mapped_summaries_text = []
        for res_item in map_results:
            mapped_summaries_text.append(
                f"### Document: {res_item['filename']}\n{res_item['axes_summary']}"
            )
        all_mapped_str = "\n\n---\n\n".join(mapped_summaries_text)

        doc_names = [d.filename for d in docs]
        axes_str = ", ".join(axes)

        reduce_sys_instruction = (
            "You are a Distinguished AI Systems & Computing Researcher specializing in comparative literature synthesis.\n"
            "Given the extracted technical notes for multiple research papers, produce a comprehensive, publication-grade comparative analysis.\n\n"
            "YOUR OUTPUT MUST CONTAIN:\n"
            "1. ## Executive Comparative Synthesis: High-level contrast of goals, core paradigms, and primary trade-offs.\n"
            "2. ## Comparative Evaluation Matrix: A detailed, beautifully aligned Markdown Table with columns:\n"
            f"   | Technical Axis | {' | '.join(doc_names)} | Key Distinction / Trade-off |\n"
            "   Fill every row for each specified axis thoroughly.\n"
            "3. ## Deep Architectural Trade-offs & Synergies: How the papers differ in practicality, and whether their techniques can be combined."
        )

        reduce_prompt = (
            f"Comparison Focus / Query: {query or 'Comprehensive multi-document comparative analysis'}\n\n"
            f"Target Comparison Axes:\n{axes_str}\n\n"
            f"Per-Document Extracted Notes:\n{all_mapped_str}\n\n"
            "Synthesize the complete comparative report now:"
        )

        synthesis_result = await LLMService.generate_response(
            system_instruction=reduce_sys_instruction,
            user_prompt=reduce_prompt,
            temperature=0.2
        )

        return {
            "query": query,
            "axes": axes,
            "documents_compared": [
                {"id": str(d.id), "filename": d.filename, "file_type": d.file_type}
                for d in docs
            ],
            "map_results": map_results,
            "synthesis": synthesis_result
        }
