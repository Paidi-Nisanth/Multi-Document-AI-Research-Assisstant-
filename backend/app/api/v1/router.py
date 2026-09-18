from fastapi import APIRouter
from app.api.v1 import auth, documents, search, chat, conversations, flashcards

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(search.router, prefix="/search", tags=["Search & Retrieval"])
api_router.include_router(chat.router, prefix="/chat", tags=["RAG Chat & Synthesis"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations & Memory"])
api_router.include_router(flashcards.router, prefix="/flashcards", tags=["Study Flashcards"])
