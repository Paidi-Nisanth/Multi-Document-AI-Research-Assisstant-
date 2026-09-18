from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.extractor import ExtractedBlock

try:
    import tiktoken
except ImportError:
    tiktoken = None


class ChunkOutput(BaseModel):
    content: str
    chunk_index: int
    section: str
    page_number: Optional[int] = 1
    chunk_metadata: Dict[str, Any]


class StructureAwareChunker:
    def __init__(
        self,
        min_tokens: int = 150,
        target_tokens: int = 600,
        max_tokens: int = 800,
        overlap_tokens: int = 100,
        encoding_name: str = "cl100k_base"
    ):
        self.min_tokens = min_tokens
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding_name = encoding_name

        if tiktoken is not None:
            self.tokenizer = tiktoken.get_encoding(encoding_name)
        else:
            self.tokenizer = None

    def count_tokens(self, text: str) -> int:
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        # Fallback heuristic: ~4 characters per token
        return max(1, len(text) // 4)

    def chunk_blocks(self, blocks: List[ExtractedBlock]) -> List[ChunkOutput]:
        chunks: List[ChunkOutput] = []
        global_chunk_index = 0

        for block in blocks:
            text = block.content.strip()
            if not text:
                continue

            section = block.section_title or "General"
            page_num = block.page_number or 1
            token_count = self.count_tokens(text)

            if token_count <= self.max_tokens:
                # Block fits comfortably inside max token limit
                chunks.append(
                    ChunkOutput(
                        content=text,
                        chunk_index=global_chunk_index,
                        section=section,
                        page_number=page_num,
                        chunk_metadata={
                            "token_count": token_count,
                            "encoding": self.encoding_name,
                            "split_method": "structural_section"
                        }
                    )
                )
                global_chunk_index += 1
            else:
                # Block exceeds max tokens -> apply token windowing with overlap
                sub_chunks = self._recursive_token_windowing(
                    text=text,
                    section=section,
                    page_num=page_num,
                    start_index=global_chunk_index
                )
                chunks.extend(sub_chunks)
                global_chunk_index += len(sub_chunks)

        return chunks

    def _recursive_token_windowing(
        self, text: str, section: str, page_num: int, start_index: int
    ) -> List[ChunkOutput]:
        result: List[ChunkOutput] = []
        
        if not self.tokenizer:
            # Fallback character-based windowing if tiktoken unavailable
            char_window = self.target_tokens * 4
            char_overlap = self.overlap_tokens * 4
            pos = 0
            idx = start_index
            while pos < len(text):
                segment = text[pos : pos + char_window]
                result.append(
                    ChunkOutput(
                        content=segment,
                        chunk_index=idx,
                        section=section,
                        page_number=page_num,
                        chunk_metadata={
                            "token_count": len(segment) // 4,
                            "split_method": "character_fallback"
                        }
                    )
                )
                idx += 1
                pos += (char_window - char_overlap)
            return result

        tokens = self.tokenizer.encode(text)
        total_tokens = len(tokens)
        start = 0
        idx = start_index

        while start < total_tokens:
            end = min(start + self.target_tokens, total_tokens)
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)

            result.append(
                ChunkOutput(
                    content=chunk_text,
                    chunk_index=idx,
                    section=section,
                    page_number=page_num,
                    chunk_metadata={
                        "token_count": len(chunk_tokens),
                        "encoding": self.encoding_name,
                        "split_method": "token_recursive_window"
                    }
                )
            )
            idx += 1

            if end == total_tokens:
                break

            start += (self.target_tokens - self.overlap_tokens)

        return result
