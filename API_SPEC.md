# AI Interviewer & Candidate Evaluator - API Specification

## Authentication
- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login and get access/refresh tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/users/me` - Get current user profile

## Resumes
- `POST /api/v1/resumes` - Upload and parse a resume (PDF/DOCX/TXT)
- `GET /api/v1/resumes/{id}` - Get resume metadata
- `GET /api/v1/resumes/{id}/parsed` - Get extracted structured data from resume

## Jobs
- `POST /api/v1/jobs` - Ingest a new job description
- `GET /api/v1/jobs/{id}` - Get parsed job details

## Matching
- `POST /api/v1/matches` - Match a candidate resume to a job description
- `GET /api/v1/matches/{id}` - Get match results and scores

## Interviews
- `POST /api/v1/interviews` - Create a new interview session for a candidate and job
- `POST /api/v1/interviews/{id}/start` - Begin the interview state machine
- `POST /api/v1/interviews/{id}/answer` - Submit a candidate's answer to the current question
- `POST /api/v1/interviews/{id}/finish` - Complete the interview early or normally
- `GET /api/v1/interviews/{id}` - Get interview status and basic info
- `GET /api/v1/interviews/{id}/report` - Get the final interview report

## Candidates
- `GET /api/v1/candidates/{id}/skills` - Get candidate's extracted skills
- `GET /api/v1/candidates/{id}/recommendations` - Get personalized learning recommendations
