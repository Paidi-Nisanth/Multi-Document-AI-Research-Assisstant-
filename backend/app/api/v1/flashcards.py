import logging
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db, get_current_workspace, get_current_user, require_role
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.services.flashcard_service import FlashcardService

router = APIRouter()
logger = logging.getLogger(__name__)


class GenerateFlashcardsRequest(BaseModel):
    num_cards: int = 6


class FlashcardItem(BaseModel):
    id: str
    workspace_id: str
    source_chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    filename: Optional[str] = None
    section: Optional[str] = None
    page_number: Optional[int] = None
    question: str
    answer: str
    created_at: Any


@router.post("/generate/{document_id}", response_model=List[dict], status_code=status.HTTP_201_CREATED)
async def generate_flashcards(
    document_id: str,
    payload: Optional[GenerateFlashcardsRequest] = None,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(require_role([UserRole.ADMIN, UserRole.EDITOR])),
) -> Any:
    num_cards = payload.num_cards if payload else 6
    try:
        cards = await FlashcardService.generate_flashcards_for_document(
            db=db,
            document_id=document_id,
            workspace_id=str(workspace.id),
            num_cards=num_cards
        )
        return cards
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        logger.error(f"Error generating flashcards for {document_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Flashcard generation failed: {str(exc)}")


@router.get("/", response_model=List[FlashcardItem])
async def list_flashcards(
    document_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
) -> Any:
    cards = await FlashcardService.list_flashcards(
        db=db,
        workspace_id=str(workspace.id),
        document_id=document_id
    )
    return [FlashcardItem(**c) for c in cards]


@router.delete("/{flashcard_id}")
async def delete_flashcard(
    flashcard_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(require_role([UserRole.ADMIN, UserRole.EDITOR])),
) -> Any:
    deleted = await FlashcardService.delete_flashcard(
        db=db,
        workspace_id=str(workspace.id),
        flashcard_id=flashcard_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
