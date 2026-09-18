import os
import socket
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

def get_database_url() -> str:
    url = settings.DATABASE_URL
    if os.getenv("DOCKER_CONTAINER", "false").lower() == "true":
        return url
    if os.getenv("USE_POSTGRES", "false").lower() == "true":
        return url
    
    # Fast check if local Postgres instance is listening on 127.0.0.1:5432
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2)
        res = sock.connect_ex(("127.0.0.1", 5432))
        sock.close()
        if res == 0:
            return url
    except Exception:
        pass

    return "sqlite+aiosqlite:///./research_db.sqlite"

db_url = get_database_url()

engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
