import requests
import time
import sys

BASE_URL = "http://localhost:8080/api/v1"

def wait_for_task(task_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(30):
        res = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)
        if res.status_code != 200:
            print(f"Failed to fetch task {task_id}: {res.text}")
            return None
        status = res.json().get("status")
        if status == "SUCCESS":
            return res.json().get("result")
        elif status == "FAILURE":
            print(f"Task {task_id} failed: {res.json().get('error')}")
            return None
        time.sleep(2)
    print(f"Task {task_id} timed out")
    return None

def main():
    print("--- 1. Register Candidate ---")
    candidate_email = f"candidate_{int(time.time())}@example.com"
    res = requests.post(f"{BASE_URL}/auth/register", json={"email": candidate_email, "password": "password123", "first_name": "John", "last_name": "Doe"})
    assert res.status_code == 201, f"Failed to register candidate: {res.text}"
    
    print("--- 2. Login Candidate ---")
    res = requests.post(f"{BASE_URL}/auth/login", data={"username": candidate_email, "password": "password123"})
    assert res.status_code == 200, f"Failed to login candidate: {res.text}"
    candidate_token = res.json()["access_token"]
    
    print("--- 3. Upload Resume ---")
    headers = {"Authorization": f"Bearer {candidate_token}"}
    files = {"file": ("resume.txt", b"Name: John Doe\nSkills: Python, React, FastApi", "text/plain")}
    res = requests.post(f"{BASE_URL}/resumes", headers=headers, files=files)
    assert res.status_code == 201, f"Failed to upload resume: {res.text}"
    task_id = res.json()["task_id"]
    
    print("--- 4. Parse Resume (Wait for Celery) ---")
    resume_parsed = wait_for_task(task_id, candidate_token)
    assert resume_parsed is not None, "Resume parsing failed"
    resume_id = resume_parsed.get("resume_id")
    
    def promote_to_admin(email):
        import subprocess
        sql = f"UPDATE users SET role = 'ADMIN' WHERE email = '{email}';"
        subprocess.run(["docker-compose", "exec", "-T", "db", "psql", "-U", "postgres", "-d", "ai_interviewer", "-c", sql])
        
    admin_email = f"admin_{int(time.time())}@example.com"
    res = requests.post(f"{BASE_URL}/auth/register", json={"email": admin_email, "password": "adminpass", "first_name": "Admin", "last_name": "User"})
    assert res.status_code == 201, f"Failed to register admin: {res.text}"
    
    promote_to_admin(admin_email)
    
    res = requests.post(f"{BASE_URL}/auth/login", data={"username": admin_email, "password": "adminpass"})
    admin_token = res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print("--- 6. Create Job ---")
    job_payload = {
        "title": "Software Engineer",
        "description": "Python, React, FastApi developer",
        "company": "Test Co",
        "required_skills": ["Python", "FastApi"]
    }
    res = requests.post(f"{BASE_URL}/jobs", json=job_payload, headers=admin_headers)
    assert res.status_code == 201, f"Failed to create job: {res.text}"
    job_id = res.json()["id"]
    
    print("--- 7. Match Candidate ---")
    res = requests.post(f"{BASE_URL}/matches", json={"resume_id": resume_id, "job_id": job_id}, headers=admin_headers)
    assert res.status_code == 200, f"Failed to match candidate: {res.text}"
    match_id = res.json()["id"]
    
    print("--- 8. Create Interview ---")
    res = requests.post(f"{BASE_URL}/interviews", json={"resume_id": resume_id, "job_id": job_id}, headers=headers)
    assert res.status_code == 201, f"Failed to create interview: {res.text}"
    interview_id = res.json()["interview_id"]
    
    print("--- 9. Start Interview ---")
    res = requests.post(f"{BASE_URL}/interviews/{interview_id}/start", headers=headers)
    assert res.status_code == 200, f"Failed to start interview: {res.text}"
    
    print("--- 11. Submit Answer ---")
    answer_payload = {"answer_text": "I have 5 years of experience with Python."}
    res = requests.post(f"{BASE_URL}/interviews/{interview_id}/answer", json=answer_payload, headers=headers)
    assert res.status_code == 200, f"Failed to submit answer: {res.text}"
    
    print("--- 13. Finish Interview ---")
    res = requests.post(f"{BASE_URL}/interviews/{interview_id}/finish", headers=headers)
    assert res.status_code == 200, f"Failed to finish interview: {res.text}"
    
    print("--- 14. Generate Report (Wait for Celery) ---")
    task_id = res.json()["task_id"]
    report_parsed = wait_for_task(task_id, candidate_token)
    assert report_parsed is not None, "Report generation failed"
    
    print("✅ Full E2E Flow Completed Successfully!")
    print("✅ Full E2E Flow Completed Successfully!")

if __name__ == "__main__":
    main()
