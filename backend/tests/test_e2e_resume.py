# tests/test_e2e_resume.py
"""
End-to-end tests for resume generation flow.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
import time

from app.main import app
from app.models.resume_draft import ResumeStatus


@pytest.fixture
def sample_resume_payload():
    """Sample resume payload for E2E testing."""
    return {
        "profile": {
            "full_name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone": "+1-555-0199",
            "location": "New York, NY",
            "linkedin": "https://linkedin.com/in/janesmith",
            "github": "https://github.com/janesmith",
            "summary": "Full-stack engineer with 7 years experience building scalable web applications"
        },
        "experience": [
            {
                "company": "Tech Innovations Inc",
                "position": "Senior Software Engineer",
                "start_date": "2020-03",
                "end_date": "Present",
                "location": "San Francisco, CA",
                "description": "Leading development of cloud-based microservices platform",
                "achievements": [
                    "Architected and deployed microservices handling 10M+ requests/day",
                    "Reduced infrastructure costs by 35% through optimization",
                    "Mentored team of 5 junior engineers"
                ]
            },
            {
                "company": "StartupXYZ",
                "position": "Software Engineer",
                "start_date": "2017-06",
                "end_date": "2020-02",
                "location": "Austin, TX",
                "achievements": [
                    "Built RESTful APIs serving 100K+ daily active users",
                    "Implemented CI/CD pipeline reducing deployment time by 60%"
                ]
            }
        ],
        "education": [
            {
                "institution": "Massachusetts Institute of Technology",
                "degree": "M.S. Computer Science",
                "graduation_date": "2017",
                "gpa": "3.9"
            },
            {
                "institution": "University of California, Berkeley",
                "degree": "B.S. Computer Science",
                "graduation_date": "2015",
                "honors": "Magna Cum Laude"
            }
        ],
        "skills": {
            "languages": ["Python", "JavaScript", "Go", "Java"],
            "frameworks": ["FastAPI", "React", "Django", "Node.js"],
            "technical": ["Microservices", "REST APIs", "GraphQL", "System Design"],
            "tools": ["Docker", "Kubernetes", "AWS", "PostgreSQL", "Redis"],
            "certifications": ["AWS Solutions Architect", "Google Cloud Professional"]
        },
        "projects": [
            {
                "name": "Open Source CLI Tool",
                "description": "Created a popular command-line tool for developers with 5K+ GitHub stars",
                "technologies": ["Go", "Cobra", "GitHub Actions"],
                "url": "https://github.com/user/cli-tool",
                "date": "2021"
            }
        ],
        "job_description": "Senior Full-Stack Engineer position requiring Python, React, and AWS experience",
        "ai_enhancement": {
            "enhance_summary": False,
            "enhance_experience": False,
            "enhance_projects": False,
            "use_job_description": False
        },
        "template_style": "professional"
    }


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    from app.models.user import User
    return User(
        id="test_user_123",
        email="jane.smith@example.com",
        username="janesmith",
        hashed_password="hashed",
        is_active=True
    )


class TestE2EResumeGeneration:
    """End-to-end tests for resume generation."""
    
    @pytest.mark.asyncio
    async def test_complete_resume_generation_flow(self, sample_resume_payload, mock_auth_user):
        """Test complete resume generation flow from POST to completion."""
        
        # Mock dependencies
        with patch('app.api.v1.resumes_v2.get_current_active_user', return_value=mock_auth_user), \
             patch('app.services.pdf_playwright.PlaywrightPDFService.generate_pdf_from_html') as mock_pdf, \
             patch('app.services.storage.S3StorageService.upload_file') as mock_upload, \
             patch('app.services.storage.S3StorageService.get_presigned_url') as mock_url, \
             patch('app.db.mongo.get_database') as mock_get_db:
            
            # Setup mocks
            mock_pdf.return_value = b"PDF content bytes"
            mock_upload.return_value = None
            mock_url.return_value = "https://s3.example.com/resumes/test_user_123/resume.pdf"
            
            # Mock database
            mock_collection = AsyncMock()
            mock_collection.insert_one = AsyncMock()
            mock_collection.update_one = AsyncMock()
            mock_collection.find_one = AsyncMock(return_value={
                "resume_id": "test_resume_123",
                "user_id": "test_user_123",
                "status": "complete",
                "created_at": "2024-01-20T10:00:00",
                "updated_at": "2024-01-20T10:01:00",
                "completed_at": "2024-01-20T10:01:00",
                "pdf": {
                    "s3_key": "resumes/test_user_123/test_resume_123.pdf",
                    "url": "https://s3.example.com/resumes/test_user_123/resume.pdf",
                    "uploaded_at": "2024-01-20T10:01:00",
                    "file_size": 50000
                }
            })
            
            mock_db = MagicMock()
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Step 1: Create resume
                response = await client.post(
                    "/api/v1/resumes",
                    json=sample_resume_payload,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 202
                data = response.json()
                assert "resume_id" in data
                assert data["status"] in ["processing", "draft"]
                
                resume_id = data["resume_id"]
                
                # Step 2: Check status (simulate waiting for completion)
                # In real scenario, would poll until complete
                response = await client.get(
                    f"/api/v1/resumes/{resume_id}",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                status_data = response.json()
                assert status_data["resume_id"] == resume_id
    
    @pytest.mark.asyncio
    async def test_validation_error_returns_422(self, mock_auth_user):
        """Test that validation errors return 422 with details."""
        
        # Invalid payload - missing experience
        invalid_payload = {
            "profile": {
                "full_name": "John Doe",
                "email": "john@example.com"
            },
            "experience": []  # Missing required experience
        }
        
        with patch('app.api.v1.resumes_v2.get_current_active_user', return_value=mock_auth_user), \
             patch('app.db.mongo.get_database'):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/resumes",
                    json=invalid_payload,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 422
                data = response.json()
                assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_validation_error_missing_name_returns_422(self, mock_auth_user):
        """Test that missing name returns 422."""
        
        # Invalid payload - missing name
        invalid_payload = {
            "profile": {
                "full_name": "",  # Empty name
                "email": "john@example.com"
            },
            "experience": [
                {
                    "company": "Tech Corp",
                    "position": "Engineer",
                    "start_date": "2020-01"
                }
            ]
        }
        
        with patch('app.api.v1.resumes_v2.get_current_active_user', return_value=mock_auth_user), \
             patch('app.db.mongo.get_database'):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/resumes",
                    json=invalid_payload,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_resume_status_check_returns_correct_data(self, mock_auth_user):
        """Test that status check returns correct resume data."""
        
        with patch('app.api.v1.resumes_v2.get_current_active_user', return_value=mock_auth_user), \
             patch('app.db.mongo.get_database') as mock_get_db:
            
            # Mock database response
            mock_collection = AsyncMock()
            mock_collection.find_one = AsyncMock(return_value={
                "resume_id": "test_resume_456",
                "user_id": "test_user_123",
                "status": "complete",
                "created_at": "2024-01-20T10:00:00",
                "updated_at": "2024-01-20T10:01:00",
                "completed_at": "2024-01-20T10:01:00",
                "pdf": {
                    "s3_key": "resumes/test_user_123/test_resume_456.pdf",
                    "url": "https://s3.example.com/resume.pdf",
                    "uploaded_at": "2024-01-20T10:01:00"
                }
            })
            
            mock_db = MagicMock()
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/resumes/test_resume_456",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["resume_id"] == "test_resume_456"
                assert data["status"] == "complete"
                assert data["download_url"] == "https://s3.example.com/resume.pdf"
    
    @pytest.mark.asyncio
    async def test_resume_not_found_returns_404(self, mock_auth_user):
        """Test that non-existent resume returns 404."""
        
        with patch('app.api.v1.resumes_v2.get_current_active_user', return_value=mock_auth_user), \
             patch('app.db.mongo.get_database') as mock_get_db:
            
            # Mock database to return None (not found)
            mock_collection = AsyncMock()
            mock_collection.find_one = AsyncMock(return_value=None)
            
            mock_db = MagicMock()
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/resumes/nonexistent_id",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_resumes_returns_user_resumes(self, mock_auth_user):
        """Test that list endpoint returns user's resumes."""
        
        with patch('app.api.v1.resumes_v2.get_current_active_user', return_value=mock_auth_user), \
             patch('app.db.mongo.get_database') as mock_get_db:
            
            # Mock database to return list of resumes
            mock_cursor = AsyncMock()
            mock_cursor.__aiter__.return_value = [
                {
                    "resume_id": "resume_1",
                    "user_id": "test_user_123",
                    "status": "complete",
                    "created_at": "2024-01-20T10:00:00",
                    "updated_at": "2024-01-20T10:01:00",
                    "pdf": {"url": "https://s3.example.com/resume1.pdf"}
                },
                {
                    "resume_id": "resume_2",
                    "user_id": "test_user_123",
                    "status": "processing",
                    "created_at": "2024-01-20T11:00:00",
                    "updated_at": "2024-01-20T11:00:30"
                }
            ]
            
            mock_collection = MagicMock()
            mock_find = MagicMock(return_value=mock_cursor)
            mock_find.sort = MagicMock(return_value=mock_cursor)
            mock_find.skip = MagicMock(return_value=mock_cursor)
            mock_find.limit = MagicMock(return_value=mock_cursor)
            mock_cursor.sort = MagicMock(return_value=mock_cursor)
            mock_cursor.skip = MagicMock(return_value=mock_cursor)
            mock_cursor.limit = MagicMock(return_value=mock_cursor)
            mock_collection.find = MagicMock(return_value=mock_cursor)
            
            mock_db = MagicMock()
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/resumes",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, list)


class TestAIEnhancementE2E:
    """E2E tests with AI enhancement enabled."""
    
    @pytest.mark.asyncio
    async def test_resume_with_ai_enhancement(self, sample_resume_payload, mock_auth_user):
        """Test resume generation with AI enhancement enabled."""
        
        # Enable AI enhancement
        sample_resume_payload["ai_enhancement"]["enhance_summary"] = True
        sample_resume_payload["ai_enhancement"]["enhance_experience"] = True
        
        with patch('app.api.v1.resumes_v2.get_current_active_user', return_value=mock_auth_user), \
             patch('app.services.pdf_playwright.PlaywrightPDFService.generate_pdf_from_html') as mock_pdf, \
             patch('app.services.storage.S3StorageService.upload_file') as mock_upload, \
             patch('app.services.storage.S3StorageService.get_presigned_url') as mock_url, \
             patch('app.services.llm.LLMService.generate') as mock_llm, \
             patch('app.db.mongo.get_database') as mock_get_db:
            
            # Setup mocks
            mock_pdf.return_value = b"PDF content bytes"
            mock_upload.return_value = None
            mock_url.return_value = "https://s3.example.com/resume.pdf"
            mock_llm.return_value = "Enhanced content from AI"
            
            # Mock database
            mock_collection = AsyncMock()
            mock_collection.insert_one = AsyncMock()
            mock_collection.update_one = AsyncMock()
            
            mock_db = MagicMock()
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/resumes",
                    json=sample_resume_payload,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 202
                data = response.json()
                assert "resume_id" in data
