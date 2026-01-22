# tests/test_auth.py
import pytest
from httpx import AsyncClient
from jose import jwt
from datetime import datetime, timedelta
import time

from app.core.config import settings
from app.core.security import verify_access_token


@pytest.mark.asyncio
class TestAuthentication:
    """Test authentication endpoints"""
    
    async def test_login_success(self, test_client: AsyncClient, test_user):
        """Test successful login with valid credentials"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 300  # 5 minutes
        
        # Check refresh token cookie
        cookies = response.cookies
        assert "refresh_token" in cookies
        refresh_cookie = cookies["refresh_token"]
        assert refresh_cookie is not None
    
    async def test_login_invalid_email(self, test_client: AsyncClient):
        """Test login with non-existent email"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "somepassword"
            }
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
        assert "Invalid credentials" in response.json()["detail"]
    
    async def test_login_invalid_password(self, test_client: AsyncClient, test_user):
        """Test login with incorrect password"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    async def test_login_missing_fields(self, test_client: AsyncClient):
        """Test login with missing required fields"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com"}
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_login_invalid_email_format(self, test_client: AsyncClient):
        """Test login with invalid email format"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "password123"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_refresh_token_success(self, test_client: AsyncClient, test_user):
        """Test successful token refresh"""
        # First login to get refresh token
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            }
        )
        
        assert login_response.status_code == 200
        old_access_token = login_response.json()["access_token"]
        
        # Extract refresh token from cookie
        refresh_token = login_response.cookies.get("refresh_token")
        assert refresh_token is not None
        
        # Wait a moment to ensure different token
        time.sleep(1)
        
        # Refresh token
        refresh_response = await test_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        new_data = refresh_response.json()
        assert "access_token" in new_data
        assert new_data["access_token"] != old_access_token
        
        # Check new refresh token cookie
        new_refresh_token = refresh_response.cookies.get("refresh_token")
        assert new_refresh_token is not None
        assert new_refresh_token != refresh_token  # Token rotation
    
    async def test_refresh_token_no_cookie(self, test_client: AsyncClient):
        """Test token refresh without cookie"""
        response = await test_client.post("/api/v1/auth/refresh")
        
        assert response.status_code == 401
        assert "Refresh token required" in response.json()["detail"]
    
    async def test_refresh_token_invalid(self, test_client: AsyncClient):
        """Test token refresh with invalid token"""
        response = await test_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": "invalid-token-12345"}
        )
        
        assert response.status_code == 401
    
    async def test_logout_success(self, test_client: AsyncClient, test_user):
        """Test successful logout"""
        # First login
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            }
        )
        
        assert login_response.status_code == 200
        refresh_token = login_response.cookies.get("refresh_token")
        
        # Logout
        logout_response = await test_client.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": refresh_token}
        )
        
        assert logout_response.status_code == 200
        assert logout_response.json()["message"] == "Logged out successfully"
        
        # Try to refresh with old token (should fail)
        refresh_response = await test_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 401
    
    async def test_logout_no_cookie(self, test_client: AsyncClient):
        """Test logout without refresh token"""
        response = await test_client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestTokenSecurity:
    """Test JWT token security"""
    
    async def test_access_token_format(self, test_client: AsyncClient, test_user):
        """Test that access tokens are valid JWTs"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            }
        )
        
        assert response.status_code == 200
        access_token = response.json()["access_token"]
        
        # Decode without verification to check structure
        unverified = jwt.get_unverified_claims(access_token)
        
        assert "sub" in unverified  # Subject (user ID)
        assert "iat" in unverified  # Issued at
        assert "exp" in unverified  # Expiry
        assert unverified["sub"] == test_user["id"]
    
    async def test_access_token_verification(self, test_client: AsyncClient, test_user):
        """Test that access tokens can be verified"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            }
        )
        
        access_token = response.json()["access_token"]
        
        # Verify token
        payload = verify_access_token(access_token)
        
        assert payload["sub"] == test_user["id"]
        assert "iat" in payload
        assert "exp" in payload
    
    async def test_access_token_expiry(self, test_client: AsyncClient, test_user):
        """Test that access tokens expire in 5 minutes"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            }
        )
        
        access_token = response.json()["access_token"]
        payload = jwt.get_unverified_claims(access_token)
        
        # Check expiry time
        iat = datetime.fromtimestamp(payload["iat"])
        exp = datetime.fromtimestamp(payload["exp"])
        expiry_delta = exp - iat
        
        # Should be 5 minutes (300 seconds)
        assert expiry_delta.total_seconds() == 300
    
    async def test_access_token_algorithm(self, test_client: AsyncClient, test_user):
        """Test that tokens use correct algorithm"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            }
        )
        
        access_token = response.json()["access_token"]
        header = jwt.get_unverified_header(access_token)
        
        # Should use HS256 or RS256
        assert header["alg"] in ["HS256", "RS256"]
    
    async def test_refresh_token_rotation(self, test_client: AsyncClient, test_user, test_db):
        """Test that refresh tokens are rotated on use"""
        # Login to get initial refresh token
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            }
        )
        
        old_refresh_token = login_response.cookies.get("refresh_token")
        
        # Count refresh tokens in database
        old_count = await test_db.refresh_tokens.count_documents({"user_id": test_user["id"]})
        
        # Use refresh token
        refresh_response = await test_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": old_refresh_token}
        )
        
        assert refresh_response.status_code == 200
        new_refresh_token = refresh_response.cookies.get("refresh_token")
        
        # Tokens should be different (rotation)
        assert new_refresh_token != old_refresh_token
        
        # Old token should be revoked (can't use again)
        old_refresh_response = await test_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": old_refresh_token}
        )
        
        assert old_refresh_response.status_code == 401
    
    async def test_protected_endpoint_requires_auth(self, test_client: AsyncClient):
        """Test that protected endpoints require authentication"""
        response = await test_client.get("/api/v1/me")
        
        assert response.status_code == 403  # Forbidden
    
    async def test_protected_endpoint_with_valid_token(self, authenticated_client):
        """Test accessing protected endpoint with valid token"""
        client, token, user = authenticated_client
        
        response = await client.get("/api/v1/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user["email"]
    
    async def test_protected_endpoint_with_invalid_token(self, test_client: AsyncClient):
        """Test accessing protected endpoint with invalid token"""
        test_client.headers["Authorization"] = "Bearer invalid-token"
        response = await test_client.get("/api/v1/me")
        
        assert response.status_code == 401
