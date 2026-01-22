# app/api/v1/profile.py
"""
User profile management endpoints.

Provides CRUD operations for user profiles including:
- Create/update profile
- Get profile
- Delete profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import logging
from datetime import datetime

from app.models.profile import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
    UserProfile
)
from app.models.user import User
from app.db.mongo import get_database
from app.middleware.auth import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create or update user profile.
    
    If a profile already exists for the user, it will be updated.
    Otherwise, a new profile will be created.
    
    Args:
        profile_data: Profile data to create/update
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        Created/updated profile
    """
    try:
        # Check if profile already exists
        existing_profile = await db.user_profiles.find_one({"user_id": current_user.id})
        
        # Prepare profile document
        profile_dict = profile_data.model_dump()
        profile_dict["user_id"] = current_user.id
        
        if existing_profile:
            # Update existing profile
            profile_dict["created_at"] = existing_profile["created_at"]
            profile_dict["updated_at"] = datetime.utcnow()
            
            await db.user_profiles.update_one(
                {"user_id": current_user.id},
                {"$set": profile_dict}
            )
            
            logger.info(f"Updated profile for user {current_user.id}")
        else:
            # Create new profile
            profile_dict["created_at"] = datetime.utcnow()
            profile_dict["updated_at"] = datetime.utcnow()
            
            await db.user_profiles.insert_one(profile_dict)
            
            logger.info(f"Created profile for user {current_user.id}")
        
        # Return the profile
        return ProfileResponse(**profile_dict)
        
    except Exception as e:
        logger.error(f"Failed to create/update profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save profile: {str(e)}"
        )


@router.get("/", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get current user's profile.
    
    Args:
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        User profile
        
    Raises:
        HTTPException: If profile not found
    """
    try:
        profile = await db.user_profiles.find_one({"user_id": current_user.id})
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Please create a profile first."
            )
        
        # Remove MongoDB _id field
        profile.pop("_id", None)
        
        return ProfileResponse(**profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve profile: {str(e)}"
        )


@router.patch("/", response_model=ProfileResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Partially update user profile.
    
    Only provided fields will be updated. Null/missing fields are ignored.
    
    Args:
        profile_update: Fields to update
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        Updated profile
        
    Raises:
        HTTPException: If profile not found
    """
    try:
        # Check if profile exists
        existing_profile = await db.user_profiles.find_one({"user_id": current_user.id})
        
        if not existing_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Please create a profile first."
            )
        
        # Prepare update data (exclude None values)
        update_data = profile_update.model_dump(exclude_none=True)
        
        if not update_data:
            # No fields to update
            existing_profile.pop("_id", None)
            return ProfileResponse(**existing_profile)
        
        # Add updated_at timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        # Update profile
        await db.user_profiles.update_one(
            {"user_id": current_user.id},
            {"$set": update_data}
        )
        
        # Get updated profile
        updated_profile = await db.user_profiles.find_one({"user_id": current_user.id})
        updated_profile.pop("_id", None)
        
        logger.info(f"Partially updated profile for user {current_user.id}")
        
        return ProfileResponse(**updated_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete user profile.
    
    Warning: This will permanently delete the profile.
    Existing resumes will retain their profile snapshots.
    
    Args:
        current_user: Authenticated user
        db: Database connection
        
    Raises:
        HTTPException: If profile not found
    """
    try:
        result = await db.user_profiles.delete_one({"user_id": current_user.id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        logger.info(f"Deleted profile for user {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete profile: {str(e)}"
        )


@router.get("/exists", response_model=dict)
async def check_profile_exists(
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Check if user has a profile.
    
    Useful for onboarding flows to determine if profile setup is needed.
    
    Args:
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        {"exists": bool, "completed": bool}
    """
    try:
        profile = await db.user_profiles.find_one({"user_id": current_user.id})
        
        if not profile:
            return {"exists": False, "completed": False}
        
        # Check if profile is "complete" (has minimum required fields)
        has_experience = len(profile.get("experience", [])) > 0
        has_education = len(profile.get("education", [])) > 0
        has_skills = len(profile.get("skills", [])) > 0
        
        completed = has_experience or has_education or has_skills
        
        return {"exists": True, "completed": completed}
        
    except Exception as e:
        logger.error(f"Failed to check profile existence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check profile: {str(e)}"
        )
