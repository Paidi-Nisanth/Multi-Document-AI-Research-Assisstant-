import re
from typing import List, Dict, Any, Tuple


class CitationParser:
    @staticmethod
    def parse_citations(
        llm_response: str,
        source_map: Dict[int, Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parses citation markers like [1], [2], [1, 3] from LLM response text
        and maps them back to rich source chunk metadata.
        Returns: (cleaned_response_text, list_of_citation_objects)
        """
        citation_pattern = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
        matches = citation_pattern.findall(llm_response)

        cited_source_ids = set()
        for match in matches:
            ids = [int(i.strip()) for i in match.split(",") if i.strip().isdigit()]
            cited_source_ids.update(ids)

        citations_list: List[Dict[str, Any]] = []
        for sid in sorted(cited_source_ids):
            if sid in source_map:
                src = source_map[sid]
                citations_list.append({
                    "citation_id": sid,
                    "chunk_id": src.get("chunk_id"),
                    "document_id": src.get("document_id"),
                    "filename": src.get("filename"),
                    "section": src.get("section"),
                    "page_number": src.get("page_number"),
                    "content": src.get("content"),
                    "similarity_score": src.get("similarity_score"),
                    "rerank_score": src.get("rerank_score"),
                })

        return llm_response, citations_list
