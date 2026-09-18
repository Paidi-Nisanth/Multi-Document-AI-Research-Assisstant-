from sqlalchemy import Column, String, Text, ForeignKey
from app.db.base_class import Base

class Flashcard(Base):
    __tablename__ = "flashcards"

    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True, index=True)
    
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
