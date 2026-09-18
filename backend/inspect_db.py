import asyncio
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.models.user import User
from app.models.workspace import Workspace

async def inspect():
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        workspaces = (await db.execute(select(Workspace))).scalars().all()
        docs = (await db.execute(select(Document))).scalars().all()
        chunks_count = (await db.execute(select(func.count(Chunk.id)))).scalar()
        embs_count = (await db.execute(select(func.count(Embedding.id)))).scalar()

        print(f"=== DB INSPECTION ===")
        print(f"Users Count: {len(users)}")
        for u in users:
            print(f"  User: {u.email} | Workspace ID: {u.workspace_id}")
        
        print(f"Workspaces Count: {len(workspaces)}")
        for w in workspaces:
            print(f"  Workspace: {w.name} | ID: {w.id}")

        print(f"Documents Count: {len(docs)}")
        for d in docs:
            print(f"  Doc: {d.filename} | Status: {d.status} | Workspace ID: {d.workspace_id}")

        print(f"Total Chunks: {chunks_count}")
        print(f"Total Embeddings: {embs_count}")

        # Test search query "MX" across all chunks
        mx_chunks = (await db.execute(select(Chunk).where(Chunk.content.ilike("%MX%")))).scalars().all()
        print(f"\nChunks containing 'MX': {len(mx_chunks)}")
        for mc in mx_chunks[:5]:
            print(f"  [Doc {mc.document_id}] Chunk {mc.id} | Section: {mc.section}")
            print(f"  Content snippet: {mc.content[:150]}...")

if __name__ == '__main__':
    asyncio.run(inspect())
