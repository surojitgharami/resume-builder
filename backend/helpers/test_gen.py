
import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000"
EMAIL = "test_user_01@example.com"
PASSWORD = "ComplexPassword123!"

def login():
    try:
        # Corrected login path
        resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
        resp.raise_for_status()
        return resp.json()["access_token"]
    except Exception as e:
        print(f"Login failed: {e}")
        # Try registering if login fails
        try:
            print("Trying to register...")
            reg = requests.post(f"{BASE_URL}/api/v1/register", json={
                "email": EMAIL, 
                "password": PASSWORD,
                "full_name": "Test User"
            })
            reg.raise_for_status()
            # Login again
            resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
            return resp.json()["access_token"]
        except Exception as e2:
            print(f"Registration failed: {e2}")
            sys.exit(1)

def generate_resume(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "profile": {
            "full_name": "Test User",
            "email": EMAIL,
            "phone": "1234567890",
            "location": "NY",
            "linkedin": "",
            "github": "",
            "website": "",
            "summary": "Software Engineer",
            "awards": [],
            "languages": [],
            "interests": []
        },
        "experience": [{
            "company": "Tech Corp",
            "position": "Dev",
            "start_date": "2020-01",
            "end_date": "Present",
            "achievements": ["Built things"]
        }],
        "education": [{
            "institution": "Uni",
            "degree": "CS",
            "graduation_date": "2020"
        }],
        "skills": {
            "technical": ["Python"],
            "languages": [],
            "soft_skills": [],
            "frameworks": [],
            "tools": []
        },
        "projects": [],
        "job_description": "Software Job",
        "ai_enhancement": {
            "enhance_summary": False,
            "enhance_experience": False,
            "enhance_projects": False
        },
        "template_style": "professional"
    }
    
    print("Sending generation request...")
    resp = requests.post(f"{BASE_URL}/api/v1/resumes", json=payload, headers=headers)
    if resp.status_code != 202:
        print(f"Generation request failed: {resp.status_code} {resp.text}")
        return None
    
    return resp.json()["resume_id"]

def poll_status(token, resume_id):
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Polling status for {resume_id}...")
    
    for _ in range(30): # Wait 30s max
        resp = requests.get(f"{BASE_URL}/api/v1/resumes/{resume_id}", headers=headers)
        if resp.status_code != 200:
            print(f"Status check failed: {resp.status_code}")
            time.sleep(1)
            continue
            
        data = resp.json()
        status = data["status"]
        print(f"Status: {status}")
        
        if status == "complete":
            print(f"SUCCESS! Download URL: {data.get('download_url')}")
            return True
        elif status == "error":
            print(f"FAILURE! Msg: {data.get('error_message')}")
            print(f"Code: {data.get('error_code')}")
            return False
            
        time.sleep(1)
        
    print("Timed out waiting for completion")
    return False

if __name__ == "__main__":
    token = login()
    resume_id = generate_resume(token)
    if resume_id:
        poll_status(token, resume_id)
