from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None
from app.db.base_class import Base

class QueryCache(Base):
    __tablename__ = "query_cache"

    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    query_embedding = Column(Vector(384) if Vector else Text, nullable=False)
    response_text = Column(Text, nullable=False)
    citations = Column(JSON, default=[], nullable=False)
    ttl_timestamp = Column(DateTime(timezone=True), nullable=True)
