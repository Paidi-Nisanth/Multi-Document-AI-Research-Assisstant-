from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.orm import relationship
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None
from app.db.base_class import Base

class Embedding(Base):
    __tablename__ = "embeddings"

    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # 384 dimensions for bge-small-en-v1.5
    embedding = Column(Vector(384) if Vector else Text, nullable=False)

    chunk = relationship("Chunk", back_populates="embedding")
