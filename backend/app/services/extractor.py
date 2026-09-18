import os
import re
from typing import List, Optional
from pydantic import BaseModel

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import docx
except ImportError:
    docx = None


class ExtractedBlock(BaseModel):
    content: str
    page_number: Optional[int] = None
    section_title: Optional[str] = "General"


class DocumentExtractor:
    @staticmethod
    def extract(file_path: str, file_type: str) -> List[ExtractedBlock]:
        ext = file_type.lower().lstrip(".")
        if ext == "pdf":
            return DocumentExtractor._extract_pdf(file_path)
        elif ext in ["docx", "doc"]:
            return DocumentExtractor._extract_docx(file_path)
        elif ext in ["txt", "md"]:
            return DocumentExtractor._extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type for extraction: {file_type}")

    @staticmethod
    def _extract_pdf(file_path: str) -> List[ExtractedBlock]:
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) is not installed.")
        
        blocks: List[ExtractedBlock] = []
        doc = fitz.open(file_path)
        current_section = "Document Header"

        heading_pattern = re.compile(
            r"^(?:(?:\d+\.)*\d+\s+)?[A-Z][A-Za-z0-9\s,\-:\'\"]{2,60}$"
        )

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Use 1-indexed page numbers
            page_index = page_num + 1
            page_text = page.get_text("text")

            lines = page_text.split("\n")
            current_block_lines = []

            for line in lines:
                clean_line = line.strip()
                if not clean_line:
                    continue

                # Heading heuristic check
                if (
                    len(clean_line) < 80
                    and (clean_line.isupper() or heading_pattern.match(clean_line))
                    and not clean_line.endswith(".")
                ):
                    # Flush accumulated lines under previous section
                    if current_block_lines:
                        blocks.append(
                            ExtractedBlock(
                                content="\n".join(current_block_lines),
                                page_number=page_index,
                                section_title=current_section,
                            )
                        )
                        current_block_lines = []

                    current_section = clean_line
                else:
                    current_block_lines.append(clean_line)

            if current_block_lines:
                blocks.append(
                    ExtractedBlock(
                        content="\n".join(current_block_lines),
                        page_number=page_index,
                        section_title=current_section,
                    )
                )

        doc.close()
        return blocks

    @staticmethod
    def _extract_docx(file_path: str) -> List[ExtractedBlock]:
        if docx is None:
            raise RuntimeError("python-docx is not installed.")

        doc = docx.Document(file_path)
        blocks: List[ExtractedBlock] = []
        current_section = "Document Header"
        current_lines = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            style_name = p.style.name if p.style else ""
            is_heading = style_name.startswith("Heading") or (
                len(text) < 80 and text.isupper() and not text.endswith(".")
            )

            if is_heading:
                if current_lines:
                    blocks.append(
                        ExtractedBlock(
                            content="\n".join(current_lines),
                            page_number=1,
                            section_title=current_section,
                        )
                    )
                    current_lines = []
                current_section = text
            else:
                current_lines.append(text)

        if current_lines:
            blocks.append(
                ExtractedBlock(
                    content="\n".join(current_lines),
                    page_number=1,
                    section_title=current_section,
                )
            )

        return blocks

    @staticmethod
    def _extract_txt(file_path: str) -> List[ExtractedBlock]:
        blocks: List[ExtractedBlock] = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        lines = content.splitlines()
        current_section = "Document Header"
        current_lines = []

        for line in lines:
            clean_line = line.strip()
            if not clean_line:
                continue

            # Markdown heading or uppercase heading check
            if clean_line.startswith("#") or (
                len(clean_line) < 80 and clean_line.isupper() and not clean_line.endswith(".")
            ):
                if current_lines:
                    blocks.append(
                        ExtractedBlock(
                            content="\n".join(current_lines),
                            page_number=1,
                            section_title=current_section,
                        )
                    )
                    current_lines = []
                current_section = clean_line.lstrip("#").strip()
            else:
                current_lines.append(clean_line)

        if current_lines:
            blocks.append(
                ExtractedBlock(
                    content="\n".join(current_lines),
                    page_number=1,
                    section_title=current_section,
                )
            )

        return blocks
