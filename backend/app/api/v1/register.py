# app/api/v1/register.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import uuid

from app.models.user import UserCreate, UserResponse, User, UserProfile
from app.core.security import hash_password, sanitize_input
from app.db.mongo import get_database
from app.middleware.rate_limit import check_rate_limit
from app.middleware.auth import get_current_user
from app.core.config import settings

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Register a new user account.
    
    Args:
        request: FastAPI request object
        user_data: User registration data
        db: Database connection
        
    Returns:
        Created user response
        
    Raises:
        HTTPException: If email already exists or registration fails
    """
    # Rate limiting
    await check_rate_limit(
        request,
        "register",
        max_requests=5,
        window_seconds=3600
    )
    
    users_coll = db["users"]
    
    # Check if user already exists
    existing_user = await users_coll.find_one({"email": user_data.email.lower()})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = hash_password(user_data.password)
    
    # Sanitize user input
    sanitized_full_name = sanitize_input(user_data.full_name)
    
    # Create user document
    user_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    user = User(
        _id=user_id,
        email=user_data.email.lower(),
        password_hash=password_hash,
        profile=UserProfile(
            full_name=sanitized_full_name,
            skills=[],
            experience=[],
            education=[],
            certifications=[]
        ),
        created_at=now,
        updated_at=now,
        is_active=True,
        is_verified=False,
        auth={
            "last_login": None,
            "login_count": 0,
            "failed_login_attempts": 0
        }
    )
    
    # Insert into database
    user_dict = user.dict(by_alias=True, exclude={"id"})
    user_dict["_id"] = user_id
    
    try:
        await users_coll.insert_one(user_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
    
    # Return user response
    return UserResponse(
        id=user_id,
        email=user.email,
        profile=user.profile,
        created_at=user.created_at,
        is_active=user.is_active,
        is_verified=user.is_verified
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information.
    
    Args:
        current_user: Authenticated user from dependency
        
    Returns:
        User information
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        profile=current_user.profile,
        created_at=current_user.created_at,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified
    )
