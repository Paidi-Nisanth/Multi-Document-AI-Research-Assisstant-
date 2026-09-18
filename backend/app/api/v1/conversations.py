import uuid
import logging
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_db, get_current_user, get_current_workspace
from app.models.user import User
from app.models.workspace import Workspace
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole

router = APIRouter()
logger = logging.getLogger(__name__)


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Research Session"


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: List[Any] = []
    created_at: Any


class ConversationDetailOut(BaseModel):
    id: str
    title: str
    summary_memory: Optional[str] = None
    created_at: Any
    updated_at: Any
    messages: List[MessageOut] = []


class ConversationListItem(BaseModel):
    id: str
    title: str
    summary_memory: Optional[str] = None
    message_count: int
    created_at: Any
    updated_at: Any


@router.get("/", response_model=List[ConversationListItem])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.workspace_id == str(workspace.id),
            Conversation.user_id == str(user.id)
        )
        .order_by(desc(Conversation.updated_at))
    )
    res = await db.execute(stmt)
    convs = res.scalars().all()

    return [
        ConversationListItem(
            id=str(c.id),
            title=c.title,
            summary_memory=c.summary_memory,
            message_count=len(c.messages) if c.messages else 0,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in convs
    ]


@router.post("/", response_model=ConversationListItem, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    new_conv = Conversation(
        id=str(uuid.uuid4()),
        workspace_id=str(workspace.id),
        user_id=str(user.id),
        title=payload.title or "New Research Session",
        summary_memory=None,
    )
    db.add(new_conv)
    await db.commit()
    await db.refresh(new_conv)

    return ConversationListItem(
        id=str(new_conv.id),
        title=new_conv.title,
        summary_memory=new_conv.summary_memory,
        message_count=0,
        created_at=new_conv.created_at,
        updated_at=new_conv.updated_at,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == str(conversation_id),
            Conversation.workspace_id == str(workspace.id),
        )
    )
    res = await db.execute(stmt)
    conv = res.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    sorted_messages = sorted(conv.messages or [], key=lambda m: m.created_at)

    return ConversationDetailOut(
        id=str(conv.id),
        title=conv.title,
        summary_memory=conv.summary_memory,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageOut(
                id=str(m.id),
                role=m.role.value if hasattr(m.role, "value") else str(m.role).lower(),
                content=m.content,
                citations=m.citations or [],
                created_at=m.created_at,
            )
            for m in sorted_messages
        ],
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> Any:
    stmt = select(Conversation).where(
        Conversation.id == str(conversation_id),
        Conversation.workspace_id == str(workspace.id),
    )
    res = await db.execute(stmt)
    conv = res.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conv)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
