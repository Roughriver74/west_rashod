"""Authentication schemas."""
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.db.models import UserRoleEnum


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


class UserLogin(BaseModel):
    """Login request."""
    username: str
    password: str


class UserRegister(BaseModel):
    """Register request."""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    department_id: Optional[int] = None


class UserBase(BaseModel):
    """Base user schema."""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRoleEnum = UserRoleEnum.USER
    department_id: Optional[int] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    """Create user schema."""
    password: str


class UserUpdate(BaseModel):
    """Update user schema."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    department_id: Optional[int] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserInDB(UserBase):
    """User in database."""
    id: int
    is_verified: bool = False
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    """User response (without password)."""
    pass
