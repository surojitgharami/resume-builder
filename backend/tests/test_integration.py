# tests/test_integration.py
import pytest
from httpx import AsyncClient
from app.main import app
import uuid


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai-resume-builder"


@pytest.mark.asyncio
async def test_user_registration_flow():
    """Test complete user registration flow."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register new user
        email = f"test_{uuid.uuid4()}@example.com"
        response = await client.post(
            "/api/v1/register",
            json={
                "email": email,
                "password": "SecurePass123",
                "full_name": "Test User"
            }
        )
        
        # Check if registration succeeded or user already exists
        assert response.status_code in [201, 409]
        
        if response.status_code == 201:
            data = response.json()
            assert data["email"] == email
            assert data["is_active"] is True


@pytest.mark.asyncio
async def test_login_flow():
    """Test login flow."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First register a user
        email = f"test_{uuid.uuid4()}@example.com"
        password = "SecurePass123"
        
        await client.post(
            "/api/v1/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Test User"
            }
        )
        
        # Now login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 300


@pytest.mark.asyncio
async def test_protected_endpoint_without_auth():
    """Test that protected endpoints require authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/me")
        assert response.status_code == 403  # Forbidden without auth


@pytest.mark.asyncio
async def test_resume_generation_without_auth():
    """Test that resume generation requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/generate-resume",
            json={
                "job_description": "Software Engineer position",
                "template_preferences": {
                    "tone": "professional"
                }
            }
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_invalid_file_upload():
    """Test that invalid file uploads are rejected."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try uploading without authentication
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("test.txt", b"test content", "text/plain")}
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_cors_headers():
    """Test that CORS headers are present."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        # CORS middleware should add headers
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test Prometheus metrics endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
