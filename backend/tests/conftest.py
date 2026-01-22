# tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from httpx import AsyncClient
import uuid
from datetime import datetime

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserProfile
from app.main import app
from app.db.mongo import get_database


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def mongo_client() -> AsyncGenerator:
    """Create MongoDB client for testing"""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    yield client
    client.close()


@pytest.fixture(scope="function")
async def clean_database(mongo_client):
    """Clean test database before each test"""
    db = mongo_client[f"{settings.MONGO_DB_NAME}_test"]
    
    # Drop all collections
    for collection_name in await db.list_collection_names():
        await db[collection_name].drop()
    
    yield db
    
    # Clean up after test
    for collection_name in await db.list_collection_names():
        await db[collection_name].drop()


@pytest.fixture
async def test_db(mongo_client):
    """Get test database instance"""
    db = mongo_client[f"{settings.MONGO_DB_NAME}_test"]
    
    # Clean before test
    await db.users.delete_many({})
    await db.resumes.delete_many({})
    await db.uploads.delete_many({})
    await db.refresh_tokens.delete_many({})
    
    yield db
    
    # Clean after test
    await db.users.delete_many({})
    await db.resumes.delete_many({})
    await db.uploads.delete_many({})
    await db.refresh_tokens.delete_many({})


@pytest.fixture
async def test_client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Create HTTP test client with database override"""
    
    # Override get_database dependency
    async def override_get_database():
        return test_db
    
    app.dependency_overrides[get_database] = override_get_database
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test User"
    }


@pytest.fixture
async def test_user(test_db, sample_user) -> Dict[str, Any]:
    """Create a test user in database and return user data with ID"""
    user_id = str(uuid.uuid4())
    
    user = User(
        _id=user_id,
        email=sample_user["email"],
        password_hash=hash_password(sample_user["password"]),
        profile=UserProfile(
            full_name=sample_user["full_name"],
            skills=["Python", "FastAPI", "React"],
            experience=[
                {
                    "title": "Software Engineer",
                    "company": "Test Corp",
                    "start_date": "2020-01",
                    "end_date": "2023-12",
                    "description": "Developed applications"
                }
            ],
            education=[
                {
                    "degree": "BS Computer Science",
                    "institution": "Test University",
                    "graduation_date": "2020"
                }
            ]
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True,
        is_verified=False
    )
    
    # Insert into database
    user_dict = user.dict(by_alias=True)
    await test_db.users.insert_one(user_dict)
    
    # Return user data with password for login tests
    return {
        "id": user_id,
        "email": sample_user["email"],
        "password": sample_user["password"],
        "user_object": user
    }


@pytest.fixture
async def authenticated_client(test_client: AsyncClient, test_user: Dict[str, Any]) -> tuple[AsyncClient, str, Dict[str, Any]]:
    """Create authenticated client with access token"""
    # Login
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": test_user["password"]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    access_token = data["access_token"]
    
    # Set authorization header
    test_client.headers["Authorization"] = f"Bearer {access_token}"
    
    return test_client, access_token, test_user


@pytest.fixture
def sample_job_description():
    """Sample job description for testing"""
    return """
    Senior Software Engineer
    
    We are seeking a Senior Software Engineer with 5+ years of experience in Python,
    FastAPI, and React. Strong background in microservices architecture and cloud
    deployment (AWS/GCP) is required.
    
    Responsibilities:
    - Design and implement scalable backend services
    - Lead technical discussions and code reviews
    - Mentor junior engineers
    
    Requirements:
    - 5+ years Python development
    - Experience with FastAPI or similar frameworks
    - Strong understanding of RESTful APIs
    - Experience with Docker and Kubernetes
    """
