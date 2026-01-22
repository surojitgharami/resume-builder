# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from app.core.security import create_access_token, verify_password
from app.db.mongo import get_database

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token() -> tuple[str, str, str]:
    token_id = str(uuid.uuid4())
    raw_token = uuid.uuid4().hex + uuid.uuid4().hex
    hashed = hash_refresh_token(raw_token)
    return token_id, raw_token, hashed


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    users_coll = db["users"]
    refresh_tokens_coll = db["refresh_tokens"]
    
    user = await users_coll.find_one({"email": payload.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": str(user["_id"])},
        expires_delta=300
    )
    
    token_id, raw_refresh, hashed_refresh = create_refresh_token()
    
    await refresh_tokens_coll.insert_one({
        "token_id": token_id,
        "user_id": user["_id"],
        "refresh_token_hash": hashed_refresh,
        "issued_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30),
        "revoked": False,
        "device_info": {
            "ip": None,
            "user_agent": None
        }
    })
    
    await users_coll.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"last_login": datetime.utcnow()},
            "$inc": {"login_count": 1}
        }
    )
    
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=30 * 24 * 3600,
        path="/"
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=300
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")
    
    refresh_tokens_coll = db["refresh_tokens"]
    
    hashed = hash_refresh_token(refresh_token)
    
    token_record = await refresh_tokens_coll.find_one({
        "refresh_token_hash": hashed,
        "revoked": False
    })
    
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if token_record["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    await refresh_tokens_coll.update_one(
        {"_id": token_record["_id"]},
        {"$set": {"revoked": True}}
    )
    
    new_token_id, new_raw_refresh, new_hashed_refresh = create_refresh_token()
    
    await refresh_tokens_coll.insert_one({
        "token_id": new_token_id,
        "user_id": token_record["user_id"],
        "refresh_token_hash": new_hashed_refresh,
        "issued_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30),
        "revoked": False,
        "device_info": token_record.get("device_info", {})
    })
    
    access_token = create_access_token(
        data={"sub": str(token_record["user_id"])},
        expires_delta=300
    )
    
    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=30 * 24 * 3600,
        path="/"
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=300
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    refresh_tokens_coll = db["refresh_tokens"]
    
    if refresh_token:
        hashed = hash_refresh_token(refresh_token)
        
        await refresh_tokens_coll.update_many(
            {"refresh_token_hash": hashed},
            {"$set": {"revoked": True}}
        )
    
    response.delete_cookie(
        key="refresh_token",
        path="/"
    )
    
    return {"message": "Logged out successfully"}
