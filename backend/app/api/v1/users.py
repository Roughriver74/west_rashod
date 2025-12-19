"""User management API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, UserRoleEnum
from app.schemas.auth import UserCreate, UserUpdate, UserResponse
from app.utils.auth import get_current_active_user, get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[int] = None,
    role: Optional[UserRoleEnum] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all users (ADMIN only, or MANAGER for own department)."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view users"
        )

    query = db.query(User)

    # MANAGER can only see users in their department
    if current_user.role == UserRoleEnum.MANAGER:
        query = query.filter(User.department_id == current_user.department_id)
    elif department_id:
        query = query.filter(User.department_id == department_id)

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_term)) |
            (User.email.ilike(search_term)) |
            (User.full_name.ilike(search_term))
        )

    return query.offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user by ID."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # MANAGER can only see users in their department
    if current_user.role == UserRoleEnum.MANAGER:
        if user.department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this user"
            )

    return user


@router.post("/", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new user (ADMIN only)."""
    if current_user.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create users"
        )

    # Check if username exists
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        department_id=user_data.department_id,
        position=user_data.position,
        phone=user_data.phone,
        is_active=user_data.is_active,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user (ADMIN only)."""
    if current_user.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update users"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    update_data = user_update.model_dump(exclude_unset=True)

    # Hash password if provided
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deactivate user (ADMIN only)."""
    if current_user.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete users"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Don't allow deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    user.is_active = False
    db.commit()

    return {"message": "User deactivated"}
