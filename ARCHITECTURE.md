# AI Interviewer & Candidate Evaluator - Architecture

## 1. System Architecture
The platform is a backend-only REST API system built with FastAPI (Python 3.12+). It utilizes PostgreSQL as the primary database with pgvector for vector storage. The architecture follows a modular, service-oriented design.

Components:
- **API Layer**: FastAPI application exposing RESTful endpoints.
- **Service Layer**: Business logic for core domain entities (users, resumes, jobs, interviews).
- **AI/ML Layer**: Abstractions for LLM providers (OpenAI, etc.) and Embedding providers.
- **Data Layer**: SQLAlchemy ORM for relational data, pgvector for embeddings.
- **Background Processing**: Celery and Redis for asynchronous tasks (e.g., resume parsing, embedding generation).

## 2. Folder Structure
```text
app/
├── main.py
├── api/
│   └── v1/
│       ├── auth.py, users.py, resumes.py, jobs.py, matching.py
│       ├── interviews.py, questions.py, evaluations.py
│       └── reports.py, recommendations.py
├── core/
│   ├── config.py, security.py, logging.py, exceptions.py
├── models/
│   ├── user.py, candidate.py, resume.py, job.py, skill.py
│   ├── interview.py, question.py, answer.py, evaluation.py
│   └── recommendation.py
├── schemas/
├── services/
├── ai/
│   ├── llm/
│   ├── embeddings/
│   ├── interview/
│   ├── evaluation/
│   └── rag/
├── repositories/
├── utils/
└── tests/
```

## 3. AI Pipeline
1. **Resume Processing**: Text extraction (PyMuPDF, python-docx) -> Cleaning -> Section Detection -> AI Extraction -> Candidate Profile.
2. **Matching**: Extract skills from Job & Resume -> Embeddings -> Cosine Similarity -> Match Score.
3. **Question Generation**: Context (Resume + Job + Candidate Experience) -> AI Prompt -> Generated Questions.

## 4. RAG Architecture
1. **Ingestion**: Technical Documents -> Chunking -> Embeddings (OpenAI) -> pgvector.
2. **Retrieval**: Candidate Answer / Question Context -> Query Embedding -> pgvector Similarity Search -> Top-K Chunks.
3. **Generation**: Top-K Chunks + LLM Prompt -> Verification / Generation.

## 5. Interview State Machine
- `NOT_STARTED`: Interview created, waiting for candidate.
- `INTRODUCTION`: Initial greeting and basic questions.
- `TECHNICAL`: Domain-specific technical questions.
- `FOLLOW_UP`: Clarifications on incomplete or weak answers.
- `BEHAVIORAL`: Situational and HR questions.
- `FINALIZATION`: Closing remarks.
- `COMPLETED`: Interview finished, report generation triggered.

## 6. Security Model
- **Authentication**: JWT-based (Access/Refresh tokens), OAuth2 password flow.
- **Authorization**: Role-based access control (CANDIDATE, ADMIN).
- **Data Protection**: Passwords hashed with bcrypt/Argon2.
- **API Security**: Rate limiting, CORS, input validation via Pydantic.
