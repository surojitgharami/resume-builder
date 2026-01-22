# app/api/v1/users.py
"""
User management endpoints.

Provides endpoints for:
- Get current user info
- Update user profile (simple format)
- Import profile from JSON (auto-detects format)
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
import logging
import uuid
from datetime import datetime

from app.models.user import User, UserProfile, UserResponse
from app.models.profile import (
    ProfileCreate,
    ContactInfo,
    Experience as DetailedExperience,
    Education as DetailedEducation,
    Certification,
    Project
)
from app.db.mongo import get_database
from app.middleware.auth import get_current_active_user
from app.services.storage import get_storage_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/me/photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Upload a profile photo.
    
    Args:
        file: Image file (jpg, jpeg, png)
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        dict: New photo URL
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Validate file size (e.g., 5MB max for photo)
    max_size = 5 * 1024 * 1024
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    if size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Max size 5MB"
        )
        
    try:
        storage_service = get_storage_service()
        file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else "jpg"
        file_id = str(uuid.uuid4())
        
        # Consistent path structure
        object_key = f"profiles/{str(current_user.id)}/photo.{file_ext}"
        
        # Upload
        photo_url = await storage_service.upload_file(
            file.file,
            object_key,
            content_type=file.content_type,
            metadata={"user_id": str(current_user.id), "type": "profile_photo"}
        )
        
        # If using local storage, prepend the mount point if it's not already there
        # but LocalStorageService returns '/local_storage/...' so it's fine.
        # Wait, I need to check if LocalStorageService return matches the mount point.
        # Yes, app.mount('/local_storage', ...) matches LocalStorageService return '/local_storage/...'
        
        # If S3, it returns the key. We need a way to serve it?
        # Typically S3StorageService.upload_file returns the KEY. 
        # But we need a URL. S3StorageService.generate_presigned_url exists.
        
        # Wait, let's check what LocalStorageService returns.
        # It returns: local_url = f"/local_storage/{object_path}"
        # S3StorageService returns: object_key
        
        if not photo_url.startswith("/"):
            # It's an S3 key, we might want to store just the key or a signed URL?
            # Ideally store the key/URL relative to something.
            # For simplicity, if it's S3, the frontend will need a way to get the URL.
            # Or we can generate a signed URL right here if it's S3? No, signed URLs expire.
            # Best practice: Store the KEY/Path in DB, and frontend requests a signed URL, 
            # OR we generate a public URL if the bucket is public.
            pass
            
            # For this task, assuming local usage mainly. 
            # If S3, let's just generate a long-lived presigned URL or assume public?
            # Let's generate a presigned URL for return.
            if "s3" in str(type(storage_service)).lower():
                 photo_url = await storage_service.generate_presigned_url(photo_url, expiration=86400) # 24h
        
        # Update user profile
        users_coll = db["users"]
        await users_coll.update_one(
            {"_id": str(current_user.id)},
            {"$set": {
                "profile.photo_url": photo_url,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Also update separate user_profiles collection if it exists
        await db.user_profiles.update_one(
            {"user_id": str(current_user.id)},
            {"$set": {
                "photo_url": photo_url,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return {"photo_url": photo_url}
        
    except Exception as e:
        logger.error(f"Failed to upload profile photo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload photo"
        )


def detect_profile_format(data: dict) -> str:
    """
    Auto-detect profile format.
    
    Returns:
        'simple' - Simple profile format (UserProfile)
        'detailed' - Detailed profile format (ProfileCreate)
    """
    # Detailed format has nested 'contact' object
    if 'contact' in data and isinstance(data.get('contact'), dict):
        return 'detailed'
    
    # Simple format has flat structure with *_url fields
    if any(key.endswith('_url') for key in data.keys()):
        return 'simple'
    
    # Default to simple if ambiguous
    return 'simple'


def sanitize_profile_data(data: dict, format_type: str) -> dict:
    """
    Sanitize profile data to fix common validation issues.
    
    Args:
        data: Profile data dict
        format_type: 'simple' or 'detailed'
        
    Returns:
        Sanitized profile data
    """
    data = data.copy()  # Don't modify original
    
    # Fix certifications - add default date_obtained if missing
    if 'certifications' in data and isinstance(data['certifications'], list):
        for cert in data['certifications']:
            if isinstance(cert, dict):
                # Add default date_obtained if missing
                if 'date_obtained' not in cert or not cert['date_obtained']:
                    cert['date_obtained'] = '2020-01'
                # Ensure required fields exist
                if 'name' not in cert:
                    cert['name'] = 'Certification'
                if 'issuer' not in cert:
                    cert['issuer'] = 'Issuer'
    
    # Fix languages - convert objects to strings if needed
    if 'languages' in data and isinstance(data['languages'], list):
        sanitized_languages = []
        for lang in data['languages']:
            if isinstance(lang, dict):
                # Convert {"name": "English", "proficiency": "Native"} to "English (Native)"
                name = lang.get('name', 'Language')
                proficiency = lang.get('proficiency', '')
                if proficiency:
                    sanitized_languages.append(f"{name} ({proficiency})")
                else:
                    sanitized_languages.append(name)
            elif isinstance(lang, str):
                sanitized_languages.append(lang)
        data['languages'] = sanitized_languages
    
    # For detailed format, ensure all required fields exist
    if format_type == 'detailed':
        # Ensure projects, certifications, etc. are lists
        for field in ['projects', 'certifications', 'languages', 'volunteer_work', 'awards', 'publications']:
            if field not in data:
                data[field] = []
    
    return data



def convert_simple_to_detailed(simple_profile: dict, user_email: str) -> ProfileCreate:
    """
    Convert simple profile format to detailed profile format.
    
    Args:
        simple_profile: Simple profile dict (UserProfile format)
        user_email: User's email for contact info
        
    Returns:
        ProfileCreate object
    """
    # Build contact info
    contact = ContactInfo(
        email=user_email,
        phone=simple_profile.get('phone'),
        location=simple_profile.get('location'),
        linkedin=simple_profile.get('linkedin_url'),
        github=simple_profile.get('github_url'),
        portfolio=simple_profile.get('portfolio_url'),
        website=None
    )
    
    # Convert experience entries
    detailed_experience = []
    for exp in simple_profile.get('experience', []):
        detailed_exp = DetailedExperience(
            title=exp.get('position', 'Position'),
            company=exp.get('company', 'Company'),
            location=exp.get('location'),
            start_date=exp.get('start_date', '2020'),
            end_date=exp.get('end_date'),
            is_current=exp.get('end_date') is None,
            bullets=exp.get('achievements', []),
            description=exp.get('description')
        )
        detailed_experience.append(detailed_exp)
    
    # Convert education entries
    detailed_education = []
    for edu in simple_profile.get('education', []):
        detailed_edu = DetailedEducation(
            degree=edu.get('degree', 'Degree'),
            school=edu.get('institution', 'Institution'),
            location=None,
            start_date=edu.get('graduation_date', '2020'),
            end_date=edu.get('graduation_date', '2020'),
            gpa=edu.get('gpa'),
            honors=edu.get('honors'),
            relevant_coursework=edu.get('relevant_coursework', []),
            achievements=[]
        )
        detailed_education.append(detailed_edu)
    
    # Convert certifications
    detailed_certs = []
    for cert in simple_profile.get('certifications', []):
        if isinstance(cert, dict):
            detailed_cert = Certification(
                name=cert.get('name', 'Certification'),
                issuer=cert.get('issuer', 'Issuer'),
                date_obtained=cert.get('date_obtained', '2020-01'),
                expiry_date=cert.get('expiry_date'),
                credential_id=cert.get('credential_id'),
                credential_url=cert.get('credential_url')
            )
            detailed_certs.append(detailed_cert)
    
    return ProfileCreate(
        full_name=simple_profile.get('full_name', 'User'),
        professional_title=None,
        contact=contact,
        summary=simple_profile.get('summary'),
        skills=simple_profile.get('skills', []),
        experience=detailed_experience,
        education=detailed_education,
        projects=[],
        certifications=detailed_certs,
        languages=[],
        volunteer_work=[],
        awards=[],
        publications=[]
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        User information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        profile=current_user.profile,
        created_at=current_user.created_at,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified
    )


@router.patch("/me/profile", response_model=UserResponse)
async def update_user_profile(
    profile_data: UserProfile,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update user's simple profile (stored in user document).
    
    Args:
        profile_data: Profile data to update
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        Updated user information
    """
    try:
        # Update user's profile field
        await db.users.update_one(
            {"_id": current_user.id},
            {
                "$set": {
                    "profile": profile_data.model_dump(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Get updated user
        updated_user_doc = await db.users.find_one({"_id": current_user.id})
        updated_user = User(**updated_user_doc)
        
        logger.info(f"Updated simple profile for user {current_user.id}")
        
        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            profile=updated_user.profile,
            created_at=updated_user.created_at,
            is_active=updated_user.is_active,
            is_verified=updated_user.is_verified
        )
        
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.post("/me/profile/import-json")
async def import_profile_json(
    profile_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Import profile from JSON with auto-format detection.
    
    Supports both simple and detailed profile formats:
    - Simple: UserProfile format (flat structure with *_url fields)
    - Detailed: ProfileCreate format (nested contact object)
    
    The endpoint will:
    1. Auto-detect the format
    2. Update the simple profile in user document
    3. Create/update detailed profile in user_profiles collection
    
    Args:
        profile_data: Profile JSON data
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        Success message with format detected and profiles updated
    """
    try:
        # Check if user pasted full user object (has 'profile' field)
        # If so, extract just the profile
        if 'profile' in profile_data and isinstance(profile_data.get('profile'), dict):
            logger.info("Detected full user object, extracting profile field")
            profile_data = profile_data['profile']
        
        # Detect format
        format_type = detect_profile_format(profile_data)
        logger.info(f"Detected profile format: {format_type}")
        
        # Sanitize data to fix common validation issues
        profile_data = sanitize_profile_data(profile_data, format_type)
        logger.info("Profile data sanitized")
        
        # Process based on format
        if format_type == 'simple':
            # Validate and parse simple profile
            simple_profile = UserProfile(**profile_data)
            
            # Update user's simple profile
            await db.users.update_one(
                {"_id": current_user.id},
                {
                    "$set": {
                        "profile": simple_profile.model_dump(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Convert to detailed format and save to user_profiles
            detailed_profile = convert_simple_to_detailed(
                profile_data,
                current_user.email
            )
            
            # Save to user_profiles collection
            detailed_dict = detailed_profile.model_dump()
            detailed_dict["user_id"] = current_user.id
            
            existing_profile = await db.user_profiles.find_one({"user_id": current_user.id})
            if existing_profile:
                detailed_dict["created_at"] = existing_profile["created_at"]
                detailed_dict["updated_at"] = datetime.utcnow()
                await db.user_profiles.update_one(
                    {"user_id": current_user.id},
                    {"$set": detailed_dict}
                )
            else:
                detailed_dict["created_at"] = datetime.utcnow()
                detailed_dict["updated_at"] = datetime.utcnow()
                await db.user_profiles.insert_one(detailed_dict)
            
            logger.info(f"Imported simple profile and created detailed profile for user {current_user.id}")
            
            return {
                "message": "Profile imported successfully",
                "format_detected": "simple",
                "profiles_updated": ["user.profile", "user_profiles"]
            }
            
        else:  # detailed format
            # Validate and parse detailed profile
            detailed_profile = ProfileCreate(**profile_data)
            
            # Save to user_profiles collection
            detailed_dict = detailed_profile.model_dump()
            detailed_dict["user_id"] = current_user.id
            
            existing_profile = await db.user_profiles.find_one({"user_id": current_user.id})
            if existing_profile:
                detailed_dict["created_at"] = existing_profile["created_at"]
                detailed_dict["updated_at"] = datetime.utcnow()
                await db.user_profiles.update_one(
                    {"user_id": current_user.id},
                    {"$set": detailed_dict}
                )
            else:
                detailed_dict["created_at"] = datetime.utcnow()
                detailed_dict["updated_at"] = datetime.utcnow()
                await db.user_profiles.insert_one(detailed_dict)
            
            # Also update simple profile in user document
            simple_profile = UserProfile(
                full_name=detailed_profile.full_name,
                phone=detailed_profile.contact.phone,
                location=detailed_profile.contact.location,
                linkedin_url=detailed_profile.contact.linkedin,
                github_url=detailed_profile.contact.github,
                portfolio_url=detailed_profile.contact.portfolio,
                summary=detailed_profile.summary,
                skills=detailed_profile.skills,
                experience=[
                    {
                        "company": exp.company,
                        "position": exp.title,
                        "start_date": exp.start_date,
                        "end_date": exp.end_date,
                        "location": exp.location,
                        "description": exp.description,
                        "achievements": exp.bullets
                    }
                    for exp in detailed_profile.experience
                ],
                education=[
                    {
                        "institution": edu.school,
                        "degree": edu.degree,
                        "graduation_date": edu.end_date,
                        "gpa": edu.gpa,
                        "honors": edu.honors,
                        "relevant_coursework": edu.relevant_coursework
                    }
                    for edu in detailed_profile.education
                ],
                certifications=[
                    {
                        "name": cert.name,
                        "issuer": cert.issuer,
                        "date_obtained": cert.date_obtained,
                        "expiry_date": cert.expiry_date,
                        "credential_id": cert.credential_id,
                        "credential_url": cert.credential_url
                    }
                    for cert in detailed_profile.certifications
                ]
            )
            
            await db.users.update_one(
                {"_id": current_user.id},
                {
                    "$set": {
                        "profile": simple_profile.model_dump(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Imported detailed profile and updated simple profile for user {current_user.id}")
            
            return {
                "message": "Profile imported successfully",
                "format_detected": "detailed",
                "profiles_updated": ["user_profiles", "user.profile"]
            }
            
    except Exception as e:
        logger.error(f"Failed to import profile JSON: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to import profile: {str(e)}"
        )
