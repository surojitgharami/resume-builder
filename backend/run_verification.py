#!/usr/bin/env python
"""
Quick verification script to test all critical fixes.
"""
import sys
import traceback

def test_imports():
    """Test that all modules can be imported."""
    print("=" * 70)
    print("TESTING MODULE IMPORTS")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Import ResumeDraft models
    try:
        from app.models.resume_draft import ResumeDraft, Profile, ExperienceEntry
        print("✓ Test 1: ResumeDraft models import successfully")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 1 FAILED: {e}")
        tests_failed += 1
    
    # Test 2: Import User models
    try:
        from app.models.user import User, UserProfile
        print("✓ Test 2: User models import successfully")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 2 FAILED: {e}")
        tests_failed += 1
    
    # Test 3: Import Playwright cleanup
    try:
        from app.services.pdf_playwright import cleanup_playwright_service
        print("✓ Test 3: Playwright cleanup function exists")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 3 FAILED: {e}")
        tests_failed += 1
    
    # Test 4: Import config
    try:
        from app.core.config import settings
        print("✓ Test 4: Config imports successfully")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 4 FAILED: {e}")
        tests_failed += 1
    
    # Test 5: Import main app
    try:
        from app.main import app
        print("✓ Test 5: Main app imports successfully")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 5 FAILED: {e}")
        tests_failed += 1
    
    return tests_passed, tests_failed


def test_objectid_conversion():
    """Test ObjectId conversion logic."""
    print("\n" + "=" * 70)
    print("TESTING OBJECTID CONVERSION")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        from bson import ObjectId
        
        # Test valid ObjectId string
        test_id = '507f1f77bcf86cd799439011'
        assert ObjectId.is_valid(test_id), "Should recognize valid ObjectId"
        
        obj_id = ObjectId(test_id)
        assert isinstance(obj_id, ObjectId), "Should convert to ObjectId"
        assert str(obj_id) == test_id, "Should convert back to string"
        
        print(f"✓ Test 6: ObjectId conversion works correctly ({test_id})")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 6 FAILED: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    return tests_passed, tests_failed


def test_pydantic_model_dump():
    """Test Pydantic v2 model_dump method."""
    print("\n" + "=" * 70)
    print("TESTING PYDANTIC V2 MODEL_DUMP")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        from app.models.resume_draft import Profile, ResumeDraft, ExperienceEntry
        
        # Test Profile model_dump
        profile = Profile(
            full_name='John Doe',
            email='john@example.com'
        )
        
        assert hasattr(profile, 'model_dump'), "Profile should have model_dump method"
        data = profile.model_dump()
        assert isinstance(data, dict), "model_dump should return dict"
        assert data['full_name'] == 'John Doe', "Data should be correct"
        
        print(f"✓ Test 7: Profile model_dump works (name={data['full_name']})")
        tests_passed += 1
        
        # Test ResumeDraft model_dump
        draft = ResumeDraft(
            profile=Profile(
                full_name='Jane Smith',
                email='jane@example.com'
            ),
            experience=[
                ExperienceEntry(
                    company='Tech Corp',
                    position='Engineer',
                    start_date='2020-01'
                )
            ]
        )
        
        snapshot = draft.model_dump()
        assert isinstance(snapshot, dict), "Draft model_dump should return dict"
        assert 'profile' in snapshot, "Should have profile key"
        assert 'experience' in snapshot, "Should have experience key"
        assert len(snapshot['experience']) == 1, "Should have 1 experience"
        
        print(f"✓ Test 8: ResumeDraft model_dump works (experiences={len(snapshot['experience'])})")
        tests_passed += 1
        
    except Exception as e:
        print(f"✗ Tests 7-8 FAILED: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    return tests_passed, tests_failed


def test_resume_draft_validation():
    """Test ResumeDraft validation rules."""
    print("\n" + "=" * 70)
    print("TESTING RESUME DRAFT VALIDATION")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        from app.models.resume_draft import ResumeDraft, Profile, ExperienceEntry
        from pydantic import ValidationError
        
        # Test 1: Empty name should fail
        try:
            ResumeDraft(
                profile=Profile(full_name='', email='test@example.com'),
                experience=[ExperienceEntry(company='Test', position='Eng', start_date='2020')]
            )
            print("✗ Test 9 FAILED: Empty name should raise validation error")
            tests_failed += 1
        except (ValidationError, ValueError):
            print("✓ Test 9: Empty name validation works")
            tests_passed += 1
        
        # Test 2: Empty experience should fail
        try:
            ResumeDraft(
                profile=Profile(full_name='John Doe', email='test@example.com'),
                experience=[]
            )
            print("✗ Test 10 FAILED: Empty experience should raise validation error")
            tests_failed += 1
        except (ValidationError, ValueError):
            print("✓ Test 10: Empty experience validation works")
            tests_passed += 1
        
        # Test 3: Valid draft should succeed
        draft = ResumeDraft(
            profile=Profile(full_name='John Doe', email='test@example.com'),
            experience=[ExperienceEntry(company='Tech', position='Eng', start_date='2020')]
        )
        assert draft.profile.full_name == 'John Doe'
        print("✓ Test 11: Valid ResumeDraft creation works")
        tests_passed += 1
        
    except Exception as e:
        print(f"✗ Tests 9-11 FAILED: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    return tests_passed, tests_failed


def test_router_registration():
    """Test that all routers are registered."""
    print("\n" + "=" * 70)
    print("TESTING ROUTER REGISTRATION")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        from app.main import app
        
        # Get all routes
        routes = [route.path for route in app.routes]
        
        # Check for key routes
        assert any('/api/v1/auth' in route for route in routes), "Auth routes should exist"
        assert any('/api/v1/resumes' in route for route in routes), "Resume routes should exist"
        
        print(f"✓ Test 12: Routers registered ({len(routes)} total routes)")
        tests_passed += 1
        
        # Check specifically for resumes_v2 routes
        import os
        main_path = os.path.join(os.path.dirname(__file__), 'app', 'main.py')
        with open(main_path, 'r') as f:
            content = f.read()
        
        assert 'resumes_v2' in content, "resumes_v2 should be imported"
        print("✓ Test 13: resumes_v2 router is imported in main.py")
        tests_passed += 1
        
    except Exception as e:
        print(f"✗ Tests 12-13 FAILED: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    return tests_passed, tests_failed


def test_user_model():
    """Test User model structure."""
    print("\n" + "=" * 70)
    print("TESTING USER MODEL")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        from app.models.user import User, UserProfile
        from datetime import datetime
        
        profile = UserProfile(
            full_name='Test User',
            skills=['Python', 'FastAPI'],
            experience=[],
            education=[]
        )
        
        user = User(
            email='test@example.com',
            password_hash='hashed',
            profile=profile,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Test model_dump
        user_dict = user.model_dump()
        assert 'email' in user_dict
        assert 'profile' in user_dict
        assert user_dict['profile']['full_name'] == 'Test User'
        
        print("✓ Test 14: User model structure correct")
        tests_passed += 1
        
    except Exception as e:
        print(f"✗ Test 14 FAILED: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    return tests_passed, tests_failed


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print(" CRITICAL FIXES VERIFICATION")
    print("=" * 70)
    print()
    
    total_passed = 0
    total_failed = 0
    
    # Run all test suites
    p, f = test_imports()
    total_passed += p
    total_failed += f
    
    p, f = test_objectid_conversion()
    total_passed += p
    total_failed += f
    
    p, f = test_pydantic_model_dump()
    total_passed += p
    total_failed += f
    
    p, f = test_resume_draft_validation()
    total_passed += p
    total_failed += f
    
    p, f = test_router_registration()
    total_passed += p
    total_failed += f
    
    p, f = test_user_model()
    total_passed += p
    total_failed += f
    
    # Print summary
    print("\n" + "=" * 70)
    print(" TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Passed: {total_passed}")
    print(f"Tests Failed: {total_failed}")
    print(f"Total Tests:  {total_passed + total_failed}")
    print("=" * 70)
    
    if total_failed == 0:
        print("\n✅ ALL TESTS PASSED - All critical fixes verified!")
        return 0
    else:
        print(f"\n⚠️  {total_failed} TEST(S) FAILED - Review errors above")
        return 1


if __name__ == '__main__':
    sys.exit(main())
