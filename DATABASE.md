# AI Interviewer & Candidate Evaluator - Database Schema

## Overview
The application uses PostgreSQL as the primary relational database with SQLAlchemy ORM.
The `pgvector` extension is used for storing embeddings for RAG and semantic matching.

## Entities

### User
- `id` (UUID, PK)
- `email` (String, Unique)
- `hashed_password` (String)
- `role` (Enum: CANDIDATE, ADMIN)
- `created_at` (DateTime)
- `updated_at` (DateTime)

### CandidateProfile
- `id` (UUID, PK)
- `user_id` (UUID, FK -> User.id)
- `first_name` (String)
- `last_name` (String)
- `phone` (String)
- `education_summary` (Text)
- `experience_summary` (Text)
- `created_at` (DateTime)

### Resume
- `id` (UUID, PK)
- `candidate_id` (UUID, FK -> CandidateProfile.id)
- `file_path` (String)
- `file_type` (Enum: PDF, DOCX, TXT)
- `raw_text` (Text)
- `parsed_data` (JSONB)
- `embedding` (Vector - pgvector)
- `created_at` (DateTime)

### Job
- `id` (UUID, PK)
- `title` (String)
- `description` (Text)
- `required_skills` (JSONB)
- `preferred_skills` (JSONB)
- `seniority` (String)
- `embedding` (Vector - pgvector)
- `created_at` (DateTime)

### Skill
- `id` (UUID, PK)
- `name` (String, Unique)
- `category` (String)

### CandidateSkill
- `candidate_id` (UUID, FK -> CandidateProfile.id, PK)
- `skill_id` (UUID, FK -> Skill.id, PK)
- `proficiency_score` (Float)

### Interview
- `id` (UUID, PK)
- `candidate_id` (UUID, FK -> CandidateProfile.id)
- `job_id` (UUID, FK -> Job.id)
- `status` (Enum: NOT_STARTED, INTRODUCTION, TECHNICAL, FOLLOW_UP, BEHAVIORAL, FINALIZATION, COMPLETED)
- `started_at` (DateTime)
- `completed_at` (DateTime)

### InterviewQuestion
- `id` (UUID, PK)
- `interview_id` (UUID, FK -> Interview.id)
- `question_text` (Text)
- `category` (String)
- `difficulty` (String)
- `asked_at` (DateTime)

### InterviewAnswer
- `id` (UUID, PK)
- `question_id` (UUID, FK -> InterviewQuestion.id)
- `answer_text` (Text)
- `submitted_at` (DateTime)

### Evaluation
- `id` (UUID, PK)
- `answer_id` (UUID, FK -> InterviewAnswer.id)
- `technical_correctness` (Float)
- `relevance` (Float)
- `depth` (Float)
- `reasoning` (Float)
- `clarity` (Float)
- `overall_score` (Float)
- `feedback` (Text)
- `missing_concepts` (JSONB)

### ConversationMessage
- `id` (UUID, PK)
- `interview_id` (UUID, FK -> Interview.id)
- `role` (Enum: SYSTEM, AI, CANDIDATE)
- `content` (Text)
- `timestamp` (DateTime)

### InterviewReport
- `id` (UUID, PK)
- `interview_id` (UUID, FK -> Interview.id)
- `overall_score` (Float)
- `technical_score` (Float)
- `behavioral_score` (Float)
- `summary` (Text)
- `strong_skills` (JSONB)
- `weak_skills` (JSONB)
- `recommendation` (Text)

### Recommendation
- `id` (UUID, PK)
- `candidate_id` (UUID, FK -> CandidateProfile.id)
- `missing_skills` (JSONB)
- `learning_topics` (JSONB)
- `created_at` (DateTime)

### KnowledgeDocument
- `id` (UUID, PK)
- `domain` (String)
- `title` (String)
- `source_url` (String)

### KnowledgeChunk
- `id` (UUID, PK)
- `document_id` (UUID, FK -> KnowledgeDocument.id)
- `content` (Text)
- `embedding` (Vector - pgvector)

## Relationships
- User (1) to CandidateProfile (1)
- CandidateProfile (1) to Resumes (M)
- CandidateProfile (M) to Skills (M) via CandidateSkill
- CandidateProfile (1) to Interviews (M)
- Job (1) to Interviews (M)
- Interview (1) to InterviewQuestions (M)
- Interview (1) to ConversationMessages (M)
- Interview (1) to InterviewReport (1)
- InterviewQuestion (1) to InterviewAnswer (1)
- InterviewAnswer (1) to Evaluation (1)
- CandidateProfile (1) to Recommendations (M)
- KnowledgeDocument (1) to KnowledgeChunks (M)
