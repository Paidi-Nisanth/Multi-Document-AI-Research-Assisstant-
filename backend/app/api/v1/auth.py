import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1.deps import get_db, get_current_user
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User, UserRole
from app.models.workspace import Workspace

router = APIRouter()

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    workspace_name: str = "My Research Space"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    workspace_id: str
    role: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    workspace_id: str
    is_active: bool

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserRegister, db: AsyncSession = Depends(get_db)) -> Any:
    # Check if user email exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="A user with this email address already exists."
        )

    # Create default workspace
    ws_id = str(uuid.uuid4())
    slug_base = user_in.workspace_name.lower().replace(" ", "-")
    workspace_slug = f"{slug_base}-{uuid.uuid4().hex[:6]}"
    workspace = Workspace(id=ws_id, name=user_in.workspace_name, slug=workspace_slug)
    db.add(workspace)
    await db.flush()

    # Create user with Admin role in workspace
    u_id = str(uuid.uuid4())
    hashed_pw = get_password_hash(user_in.password)
    user = User(
        id=u_id,
        email=user_in.email,
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        role=UserRole.ADMIN,
        workspace_id=ws_id,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        subject=str(user.id),
        workspace_id=str(user.workspace_id),
        role=user.role.value
    )

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        workspace_id=str(user.workspace_id),
        role=user.role.value
    )

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")

    token = create_access_token(
        subject=str(user.id),
        workspace_id=str(user.workspace_id),
        role=user.role.value
    )

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        workspace_id=str(user.workspace_id),
        role=user.role.value
    )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> Any:
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name or "",
        role=current_user.role.value,
        workspace_id=str(current_user.workspace_id),
        is_active=current_user.is_active
    )
