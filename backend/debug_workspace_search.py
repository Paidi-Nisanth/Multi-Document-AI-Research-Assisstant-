import asyncio
import json
import urllib.request
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.workspace import Workspace
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.api.v1.search import vector_search, keyword_search, SearchQuery

async def test_ws():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == "studio_user@ai.com"))).scalars().first()
        workspace = (await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))).scalars().first()

        print(f"User: {user.email} | Workspace ID: {workspace.id}")

        # Check chunks count in this workspace
        chunks = (await db.execute(select(Chunk).where(Chunk.workspace_id == str(workspace.id)))).scalars().all()
        print(f"Chunks in workspace {workspace.id}: {len(chunks)}")

        # Check embeddings count in this workspace
        embs = (await db.execute(select(Embedding).where(Embedding.workspace_id == str(workspace.id)))).scalars().all()
        print(f"Embeddings in workspace {workspace.id}: {len(embs)}")

        query = SearchQuery(query="MX pushing the limits", top_k=5)
        
        v_res = await vector_search(query, db, workspace)
        print(f"\nVector Search Results ({len(v_res)}):")
        for r in v_res:
            print(f"  Score: {r.similarity_score} | Section: {r.section} | Content: {r.content[:100]}...")

        k_res = await keyword_search(query, db, workspace)
        print(f"\nKeyword Search Results ({len(k_res)}):")
        for r in k_res:
            print(f"  Score: {r.similarity_score} | Section: {r.section} | Content: {r.content[:100]}...")

if __name__ == '__main__':
    asyncio.run(test_ws())
