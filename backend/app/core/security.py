# app/core/security.py
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from jose import jwt, JWTError
from passlib.hash import argon2
import bleach

from app.core.config import settings

# Allowed HTML tags and attributes for sanitization
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'span', 'div'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'span': ['class'],
    'div': ['class']
}


def create_access_token(data: dict, expires_delta: int = 300) -> str:
    to_encode = data.copy()
    now = int(time.time())
    
    to_encode.update({
        "iat": now,
        "exp": now + expires_delta
    })
    
    if settings.JWT_ALGO == "RS256":
        token = jwt.encode(
            to_encode,
            settings.RS_PRIVATE_KEY,
            algorithm="RS256",
            headers={"kid": settings.RS_KID}
        )
    else:
        token = jwt.encode(
            to_encode,
            settings.JWT_SECRET,
            algorithm="HS256"
        )
    
    return token


def create_refresh_token() -> Tuple[str, str, str]:
    token_id = str(uuid.uuid4())
    raw_token = uuid.uuid4().hex + uuid.uuid4().hex
    hashed_token = hash_refresh_token(raw_token)
    return token_id, raw_token, hashed_token


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_access_token(token: str) -> Dict:
    try:
        if settings.JWT_ALGO == "RS256":
            payload = jwt.decode(
                token,
                settings.RS_PUBLIC_KEY,
                algorithms=["RS256"]
            )
        else:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=["HS256"]
            )
        
        return payload
    
    except JWTError as e:
        raise JWTError(f"Token verification failed: {str(e)}")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return argon2.verify(plain_password, password_hash)
    except Exception:
        return False


def hash_password(plain_password: str) -> str:
    return argon2.hash(plain_password)


def sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.
    
    Removes dangerous tags like <script>, <iframe>, etc. and keeps only safe tags.
    Uses strip=True to remove tags but keep text, or strip=False to escape tags.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Sanitized HTML with only safe tags and attributes
    """
    if not html_content:
        return ""
    
    # First pass: remove dangerous tags completely (including content)
    # This handles script tags where we don't want the content at all
    dangerous_patterns = [
        ('<script', '</script>'),
        ('<iframe', '</iframe>'),
        ('<object', '</object>'),
        ('<embed', '</embed>'),
    ]
    
    cleaned = html_content
    for start_tag, end_tag in dangerous_patterns:
        while start_tag.lower() in cleaned.lower():
            start_idx = cleaned.lower().find(start_tag.lower())
            if start_idx == -1:
                break
            end_idx = cleaned.lower().find(end_tag.lower(), start_idx)
            if end_idx == -1:
                # If no closing tag, remove to end
                cleaned = cleaned[:start_idx]
                break
            else:
                # Remove tag and its content
                cleaned = cleaned[:start_idx] + cleaned[end_idx + len(end_tag):]
    
    # Second pass: use bleach to sanitize remaining HTML
    return bleach.clean(
        cleaned,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )


def sanitize_input(user_input: str) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        user_input: Raw user input
        
    Returns:
        Sanitized string
    """
    if not user_input:
        return ""
    
    # Remove any null bytes
    sanitized = user_input.replace('\x00', '')
    
    # Strip leading/trailing whitespace
    sanitized = sanitized.strip()
    
    return sanitized
