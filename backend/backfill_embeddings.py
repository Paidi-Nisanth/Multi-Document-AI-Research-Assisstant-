import asyncio
import uuid
from sqlalchemy import select, delete
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.services.embedding import EmbeddingService

async def backfill():
    print("=== STARTING DENSE VECTOR EMBEDDING GENERATION (BAAI/bge-small-en-v1.5) ===")
    async with AsyncSessionLocal() as db:
        # Delete existing dummy embeddings
        await db.execute(delete(Embedding))
        await db.commit()

        # Fetch all chunks
        chunks = (await db.execute(select(Chunk))).scalars().all()
        print(f"Generating BGE embeddings for {len(chunks)} total chunks...")

        batch_size = 64
        total_created = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.content for c in batch]
            
            vectors = EmbeddingService.generate_embeddings(texts)

            for idx, c in enumerate(batch):
                emb_obj = Embedding(
                    id=str(uuid.uuid4()),
                    workspace_id=str(c.workspace_id),
                    chunk_id=str(c.id),
                    embedding=vectors[idx]
                )
                db.add(emb_obj)
                total_created += 1

            await db.commit()
            print(f"Progress: {i + len(batch)} / {len(chunks)} chunks embedded...")

        # Set all document statuses to READY
        docs = (await db.execute(select(Document))).scalars().all()
        for d in docs:
            d.status = DocumentStatus.READY
        await db.commit()

        print(f"\nSUCCESSFULLY COMPUTED & SAVED {total_created} BGE-SMALL DENSE VECTOR EMBEDDINGS!")

if __name__ == '__main__':
    asyncio.run(backfill())
