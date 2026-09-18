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


class DocumentSummarizer:
    @staticmethod
    async def summarize_document(
        db: AsyncSession,
        document_id: str,
        workspace_id: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Hierarchical Map-Reduce Document Summarization:
        1. Checks persistent cache on document.summary.
        2. Map Phase: Groups chunks into section clusters and summarizes each in parallel.
        3. Reduce Phase: Synthesizes section summaries into a publication-grade executive summary.
        4. Caches the result on the document record in PostgreSQL.
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

        # Check cache
        if doc.summary and not force_refresh:
            logger.info(f"Returning cached summary for document '{doc.filename}' ({doc.id})")
            return {
                "document_id": str(doc.id),
                "filename": doc.filename,
                "cached": True,
                "summary": doc.summary
            }

        chunks = sorted(doc.chunks or [], key=lambda c: c.chunk_index)
        if not chunks:
            return {
                "document_id": str(doc.id),
                "filename": doc.filename,
                "cached": False,
                "summary": "Document contains no extracted text chunks to summarize."
            }

        # 1. Group chunks into clusters of ~3-4 chunks (representing sections/page windows)
        cluster_size = 4
        chunk_clusters: List[List[Chunk]] = [
            chunks[i:i + cluster_size]
            for i in range(0, len(chunks), cluster_size)
        ]

        # Limit to max 6 clusters to keep summarization fast and concise
        if len(chunk_clusters) > 6:
            # Pick first 2 (intro/method), middle 2 (architecture/eval), and last 2 (results/conclusion)
            chunk_clusters = chunk_clusters[:2] + chunk_clusters[len(chunk_clusters)//2 - 1: len(chunk_clusters)//2 + 1] + chunk_clusters[-2:]

        # 2. Map Phase: Summarize each cluster in parallel
        async def summarize_cluster(cluster_idx: int, cluster: List[Chunk]) -> str:
            section_names = set(c.section for c in cluster if c.section)
            sec_header = ", ".join(section_names) if section_names else f"Part {cluster_idx + 1}"
            cluster_text = "\n\n".join([f"[{c.section or 'Section'} - p.{c.page_number}]:\n{c.content[:1000]}" for c in cluster])

            sys_instruction = (
                "You are an academic research extractor. Summarize the provided document section concisely (max 100 words), "
                "capturing technical claims, equations, and experimental metrics."
            )
            user_prompt = f"Section Context: {sec_header}\n\nContent:\n{cluster_text}\n\nGenerate section summary:"

            try:
                summary = await LLMService.generate_response(
                    system_instruction=sys_instruction,
                    user_prompt=user_prompt,
                    temperature=0.2
                )
                return f"### {sec_header}\n{summary}"
            except Exception as e:
                logger.warning(f"Failed to summarize cluster {cluster_idx}: {e}")
                return f"### {sec_header}\nTechnical content covering {sec_header}."

        map_tasks = [summarize_cluster(idx, cluster) for idx, cluster in enumerate(chunk_clusters)]
        section_summaries = await asyncio.gather(*map_tasks)
        all_sections_str = "\n\n".join(section_summaries)

        # 3. Reduce Phase: Single comprehensive synthesis
        reduce_sys_instruction = (
            "You are a Distinguished AI Research Fellow. Synthesize the section summaries of a scientific paper into a "
            "comprehensive, beautifully formatted executive research summary.\n\n"
            "STRUCTURE YOUR SUMMARY AS FOLLOWS:\n"
            "1. ## Executive Abstract: The central problem statement and core research proposition.\n"
            "2. ## Key Methodological & Architectural Innovations: Concrete algorithmic or hardware mechanisms.\n"
            "3. ## Key Empirical Findings & Metrics: Specific benchmark performance, accuracy retention, and efficiency gains.\n"
            "4. ## Primary Trade-offs & Limitations: Constraints, overheads, or scope boundaries."
        )

        reduce_prompt = (
            f"Paper Title / Filename: {doc.filename}\n\n"
            f"Section Summaries:\n{all_sections_str}\n\n"
            "Synthesize the complete publication-grade executive summary now:"
        )

        executive_summary = await LLMService.generate_response(
            system_instruction=reduce_sys_instruction,
            user_prompt=reduce_prompt,
            temperature=0.2
        )

        # 4. Cache on document record
        doc.summary = executive_summary
        await db.commit()
        await db.refresh(doc)
        logger.info(f"Generated and cached executive summary for document '{doc.filename}' ({doc.id})")

        return {
            "document_id": str(doc.id),
            "filename": doc.filename,
            "cached": False,
            "summary": executive_summary
        }
