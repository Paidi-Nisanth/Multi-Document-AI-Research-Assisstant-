import os
import tempfile
import asyncio
from app.db.session import engine
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.models.document import Document, DocumentStatus
from app.services.extractor import DocumentExtractor
from app.services.chunker import StructureAwareChunker

async def verify():
    # 1. Setup DB Schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("DB Schema initialized successfully")

    # 2. Test Extraction & Chunker on sample PDF / TXT
    sample_text = "# Introduction to AI Research\n\nAI research platforms leverage semantic chunking to enable rich multi-document context synthesis."
    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as f:
        f.write(sample_text)
        temp_path = f.name

    try:
        blocks = DocumentExtractor.extract(temp_path, "txt")
        chunker = StructureAwareChunker(target_tokens=100)
        chunks = chunker.chunk_blocks(blocks)
        print(f"Extracted {len(blocks)} blocks and generated {len(chunks)} chunks.")
        assert len(chunks) > 0, "Chunking failed"
        print("ALL SYSTEM INTEGRATION CHECKS PASSED!")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    asyncio.run(verify())
