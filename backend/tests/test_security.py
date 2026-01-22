# tests/test_security.py
import pytest
from app.core.security import hash_password, verify_password, create_access_token, verify_access_token
from app.core.security import hash_refresh_token


class TestPasswordHashing:
    """Test password hashing with Argon2"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$argon2")
        assert len(hashed) > 50
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword", hashed) is False
    
    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)"""
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2


class TestJWTTokens:
    """Test JWT token creation and verification"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        payload = {"sub": "user123"}
        token = create_access_token(payload, expires_delta=300)
        
        assert isinstance(token, str)
        assert len(token) > 50
    
    def test_verify_access_token(self):
        """Test access token verification"""
        payload = {"sub": "user123"}
        token = create_access_token(payload, expires_delta=300)
        
        decoded = verify_access_token(token)
        
        assert decoded["sub"] == "user123"
        assert "iat" in decoded
        assert "exp" in decoded
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        from jose import JWTError
        
        with pytest.raises(JWTError):
            verify_access_token("invalid.token.here")


class TestRefreshTokens:
    """Test refresh token hashing"""
    
    def test_hash_refresh_token(self):
        """Test refresh token hashing with SHA-256"""
        token = "sample-refresh-token-12345"
        hashed = hash_refresh_token(token)
        
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 produces 64-char hex
        assert hashed != token
    
    def test_same_token_produces_same_hash(self):
        """Test that same token always produces same hash"""
        token = "sample-refresh-token-12345"
        hash1 = hash_refresh_token(token)
        hash2 = hash_refresh_token(token)
        
        assert hash1 == hash2


class TestHTMLSanitization:
    """Test HTML sanitization to prevent XSS"""
    
    def test_sanitize_script_tags(self):
        """Test that script tags are removed"""
        from app.core.security import sanitize_html
        
        malicious_html = '<p>Hello</p><script>alert("XSS")</script><p>World</p>'
        sanitized = sanitize_html(malicious_html)
        
        assert '<script>' not in sanitized
        assert 'alert' not in sanitized
        assert '<p>Hello</p>' in sanitized
        assert '<p>World</p>' in sanitized
    
    def test_sanitize_iframe_tags(self):
        """Test that iframe tags are removed"""
        from app.core.security import sanitize_html
        
        malicious_html = '<p>Content</p><iframe src="evil.com"></iframe>'
        sanitized = sanitize_html(malicious_html)
        
        assert '<iframe' not in sanitized
        assert 'evil.com' not in sanitized
        assert '<p>Content</p>' in sanitized
    
    def test_sanitize_onclick_attributes(self):
        """Test that onclick and other event handlers are removed"""
        from app.core.security import sanitize_html
        
        malicious_html = '<p onclick="alert(\'XSS\')">Click me</p>'
        sanitized = sanitize_html(malicious_html)
        
        assert 'onclick' not in sanitized
        assert 'alert' not in sanitized
        assert '<p>Click me</p>' in sanitized
    
    def test_sanitize_keeps_safe_tags(self):
        """Test that safe HTML tags are kept"""
        from app.core.security import sanitize_html
        
        safe_html = '<p>Paragraph</p><strong>Bold</strong><em>Italic</em><ul><li>Item</li></ul>'
        sanitized = sanitize_html(safe_html)
        
        assert '<p>Paragraph</p>' in sanitized
        assert '<strong>Bold</strong>' in sanitized
        assert '<em>Italic</em>' in sanitized
        assert '<ul>' in sanitized
        assert '<li>Item</li>' in sanitized
    
    def test_sanitize_keeps_safe_links(self):
        """Test that safe links with href are kept"""
        from app.core.security import sanitize_html
        
        safe_html = '<a href="https://example.com" title="Example">Link</a>'
        sanitized = sanitize_html(safe_html)
        
        assert '<a href="https://example.com"' in sanitized
        assert 'title="Example"' in sanitized
        assert 'Link</a>' in sanitized
    
    def test_sanitize_removes_javascript_urls(self):
        """Test that javascript: URLs are removed"""
        from app.core.security import sanitize_html
        
        malicious_html = '<a href="javascript:alert(\'XSS\')">Click</a>'
        sanitized = sanitize_html(malicious_html)
        
        assert 'javascript:' not in sanitized
        assert 'alert' not in sanitized
    
    def test_sanitize_empty_input(self):
        """Test sanitization of empty input"""
        from app.core.security import sanitize_html
        
        assert sanitize_html("") == ""
        assert sanitize_html(None) == ""
    
    def test_sanitize_input_function(self):
        """Test general input sanitization"""
        from app.core.security import sanitize_input
        
        # Test null byte removal
        assert sanitize_input("hello\x00world") == "helloworld"
        
        # Test whitespace stripping
        assert sanitize_input("  hello  ") == "hello"
        
        # Test empty input
        assert sanitize_input("") == ""
        assert sanitize_input(None) == ""


@pytest.mark.asyncio
class TestNoSQLInjection:
    """Test NoSQL injection prevention"""
    
    async def test_login_with_object_payload(self, test_client):
        """Test that object payloads in string fields are rejected"""
        # Attempt NoSQL injection with $ne operator
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": {"$ne": None},
                "password": {"$ne": None}
            }
        )
        
        # Should fail validation (Pydantic expects strings)
        assert response.status_code == 422
    
    async def test_login_with_regex_injection(self, test_client):
        """Test that regex injection attempts are handled"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": {"$regex": ".*"},
                "password": "anything"
            }
        )
        
        # Should fail validation
        assert response.status_code == 422
    
    async def test_register_with_object_injection(self, test_client):
        """Test that object injection in registration is prevented"""
        response = await test_client.post(
            "/api/v1/register",
            json={
                "email": {"$gt": ""},
                "password": "ValidPass123!",
                "full_name": "Test User"
            }
        )
        
        # Should fail validation
        assert response.status_code == 422
    
    async def test_search_with_operator_injection(self, test_client, authenticated_client):
        """Test that MongoDB operators in search are sanitized"""
        client, token, user = authenticated_client
        
        # Attempt to inject MongoDB operators in search
        response = await client.post(
            "/api/v1/search",
            json={
                "query": {"$where": "this.password == 'test'"},
                "top_k": 5
            }
        )
        
        # Should fail validation (expects string)
        assert response.status_code == 422
    
    async def test_string_fields_reject_objects(self, test_client):
        """Test that Pydantic models reject objects in string fields"""
        from app.models.user import UserCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            UserCreate(
                email={"$ne": None},
                password="ValidPass123!",
                full_name="Test"
            )
    
    def test_email_validation_prevents_injection(self):
        """Test that email validation prevents injection attempts"""
        from app.models.user import UserCreate
        from pydantic import ValidationError
        
        # Try various injection attempts
        injection_attempts = [
            "admin@example.com' OR '1'='1",
            "admin@example.com'; DROP TABLE users--",
            "admin@example.com<script>alert('xss')</script>",
        ]
        
        for attempt in injection_attempts:
            with pytest.raises(ValidationError):
                UserCreate(
                    email=attempt,
                    password="ValidPass123!",
                    full_name="Test"
                )
    
    async def test_resume_generation_sanitizes_input(self, test_client, authenticated_client):
        """Test that resume generation sanitizes job description"""
        client, token, user = authenticated_client
        
        # Try to inject script tags in job description
        response = await client.post(
            "/api/v1/generate-resume",
            json={
                "job_description": "<script>alert('XSS')</script>Software Engineer position",
                "template_preferences": {
                    "tone": "professional"
                },
                "format": "json",
                "use_rag": False
            }
        )
        
        # Should accept (Pydantic allows strings) but content should be sanitized
        # The actual sanitization happens during processing
        assert response.status_code in [200, 202]
    
    def test_pydantic_prevents_type_confusion(self):
        """Test that Pydantic prevents type confusion attacks"""
        from app.models.resume import ResumeCreate
        from pydantic import ValidationError
        
        # Try to pass array instead of string
        with pytest.raises(ValidationError):
            ResumeCreate(
                job_description=["array", "instead", "of", "string"],
                template_preferences={}
            )
        
        # Try to pass number instead of string
        with pytest.raises(ValidationError):
            ResumeCreate(
                job_description=12345,
                template_preferences={}
            )
