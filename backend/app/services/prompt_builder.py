import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class PromptBuilder:
    @staticmethod
    def build_unified_rag_prompt(
        workspace_docs: List[Dict[str, Any]],
        query: str,
        sources: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        summary_memory: Optional[str] = None
    ) -> Tuple[str, str, Dict[int, Dict[str, Any]]]:
        """
        Builds a single, unified, universal RAG prompt schema containing:
        1. System Instruction & Grounding Rules
        2. Workspace Catalog (Macro Context)
        3. Long-term Conversation Memory (Summary of older turns)
        4. Recent Conversation History (Sliding window of last N turns)
        5. Retrieved Document Chunks (Micro Context)
        """
        # 1. Build Workspace Catalog XML
        catalog_lines = ["<workspace_catalog>"]
        if workspace_docs:
            for idx, doc in enumerate(workspace_docs, 1):
                filename = doc.get("filename", f"Document_{idx}")
                chunks_cnt = doc.get("total_chunks", 0)
                file_type = doc.get("file_type", "pdf").upper()
                catalog_lines.append(
                    f'  <document id="{idx}" filename="{filename}" type="{file_type}" total_chunks="{chunks_cnt}" />'
                )
        else:
            catalog_lines.append("  <document info=\"No documents uploaded in this workspace yet.\" />")
        catalog_lines.append("</workspace_catalog>")
        catalog_xml = "\n".join(catalog_lines)

        # 2. Build Retrieved Sources XML & Citation Mapping
        source_xml_lines = ["<retrieved_sources>"]
        source_map: Dict[int, Dict[str, Any]] = {}

        for idx, src in enumerate(sources, 1):
            source_map[idx] = src
            doc_name = src.get("filename", "Document")
            page_num = src.get("page_number", 1)
            section = src.get("section", "General")
            chunk_id = src.get("chunk_id", "")
            content = src.get("content", "").strip()

            source_xml_lines.append(
                f'  <source id="{idx}" doc="{doc_name}" page="{page_num}" section="{section}" chunk_id="{chunk_id}">\n'
                f'    {content}\n'
                f'  </source>'
            )
        source_xml_lines.append("</retrieved_sources>")
        sources_xml = "\n".join(source_xml_lines)

        # 3. Build Long-term Conversation Memory XML (if present)
        memory_xml = ""
        if summary_memory and summary_memory.strip():
            memory_xml = (
                "<conversation_memory>\n"
                f"  {summary_memory.strip()}\n"
                "</conversation_memory>"
            )

        # 4. Build Recent Conversation History XML
        history_lines = ["<recent_conversation>"]
        if chat_history:
            for msg in chat_history[-6:]:  # Last 3 turns (6 messages)
                role = msg.get("role", "user")
                text = msg.get("text", "").strip()
                history_lines.append(f'  <{role}>{text}</{role}>')
        else:
            history_lines.append("  <info>No prior conversation history.</info>")
        history_lines.append("</recent_conversation>")
        history_xml = "\n".join(history_lines)

        # 5. Universal System Instruction
        system_instruction = (
            "You are an expert AI Research Assistant operating in a Multi-Document Research Studio.\n"
            "You are provided with the following context structures:\n"
            "1. <workspace_catalog>: The full list of research papers and documents uploaded in the user's workspace.\n"
            "2. <conversation_memory>: The condensed running memory of earlier parts of this research session (if available).\n"
            "3. <recent_conversation>: The recent raw dialogue turns with the user.\n"
            "4. <retrieved_sources>: The most relevant extracted technical content chunks from the documents.\n\n"
            "INSTRUCTIONS:\n"
            "- If the user asks about workspace contents, available files, or document lists (e.g. 'what papers do you have?'), use the <workspace_catalog> to give an accurate, complete summary.\n"
            "- Maintain continuity with the research goals and decisions recorded in <conversation_memory> and <recent_conversation>.\n"
            "- If the user asks for a summary or overview of a paper, synthesize a clear summary using the document details in <workspace_catalog> and available <retrieved_sources>.\n"
            "- If the user asks technical research questions, answer thoroughly using the information in <retrieved_sources>. STRICTLY cite your sources in line using bracket notation like [1], [2], or [1, 2] corresponding to the source id attributes.\n"
            "- If the user greets you or makes conversational remarks, respond warmly and guide them on how to explore their workspace.\n"
            "- Maintain professional academic rigor, clarity, and precision."
        )

        # 6. Assemble User Prompt Payload
        prompt_parts = [catalog_xml]
        if memory_xml:
            prompt_parts.append(memory_xml)
        prompt_parts.extend([history_xml, sources_xml, f"<user_query>\n{query}\n</user_query>"])
        user_prompt = "\n\n".join(prompt_parts)

        return system_instruction, user_prompt, source_map
