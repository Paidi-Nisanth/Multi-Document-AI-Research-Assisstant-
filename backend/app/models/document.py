import enum
from sqlalchemy import Column, String, Integer, Enum, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    CHUNKED = "chunked"
    READY = "ready"
    ERROR = "error"

class Document(Base):
    __tablename__ = "documents"

    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    summary = Column(Text, nullable=True)
    doc_metadata = Column(JSON, default={}, nullable=False)

    workspace = relationship("Workspace", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
