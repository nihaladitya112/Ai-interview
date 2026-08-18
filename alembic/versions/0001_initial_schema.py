"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-15

Covers all 15 entities:
  User, CandidateProfile, Resume, Job, Skill, CandidateSkill,
  Interview, InterviewQuestion, InterviewAnswer, Evaluation,
  ConversationMessage, InterviewReport, Recommendation,
  KnowledgeDocument, KnowledgeChunk
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Enable pgvector extension
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ------------------------------------------------------------------
    # Enums
    # ------------------------------------------------------------------
    userrole = postgresql.ENUM("CANDIDATE", "ADMIN", name="userrole", create_type=False)
    userrole.create(op.get_bind(), checkfirst=True)

    filetype = postgresql.ENUM("PDF", "DOCX", "TXT", name="filetype", create_type=False)
    filetype.create(op.get_bind(), checkfirst=True)

    interviewstatus = postgresql.ENUM(
        "NOT_STARTED", "INTRODUCTION", "TECHNICAL",
        "FOLLOW_UP", "BEHAVIORAL", "FINALIZATION", "COMPLETED",
        name="interviewstatus", create_type=False,
    )
    interviewstatus.create(op.get_bind(), checkfirst=True)

    questioncategory = postgresql.ENUM(
        "TECHNICAL", "BEHAVIORAL", "SITUATIONAL", "FOLLOW_UP", "INTRODUCTION",
        name="questioncategory", create_type=False,
    )
    questioncategory.create(op.get_bind(), checkfirst=True)

    questiondifficulty = postgresql.ENUM(
        "EASY", "MEDIUM", "HARD",
        name="questiondifficulty", create_type=False,
    )
    questiondifficulty.create(op.get_bind(), checkfirst=True)

    messagerole = postgresql.ENUM(
        "SYSTEM", "AI", "CANDIDATE",
        name="messagerole", create_type=False,
    )
    messagerole.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("CANDIDATE", "ADMIN", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # candidate_profiles
    # ------------------------------------------------------------------
    op.create_table(
        "candidate_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("linkedin_url", sa.String(512)),
        sa.Column("github_url", sa.String(512)),
        sa.Column("education_summary", sa.Text()),
        sa.Column("experience_summary", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", name="uq_candidate_profiles_user_id"),
    )
    op.create_index("ix_candidate_profiles_user_id", "candidate_profiles", ["user_id"], unique=True)

    # ------------------------------------------------------------------
    # jobs
    # ------------------------------------------------------------------
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255)),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skills", postgresql.JSONB()),
        sa.Column("preferred_skills", postgresql.JSONB()),
        sa.Column("responsibilities", postgresql.JSONB()),
        sa.Column("seniority", sa.String(100)),
        sa.Column("experience_years", sa.String(50)),
        sa.Column("education_requirement", sa.String(255)),
        sa.Column("technologies", postgresql.JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_jobs_title", "jobs", ["title"])
    op.execute("ALTER TABLE jobs ADD COLUMN embedding vector(1536)")

    # ------------------------------------------------------------------
    # resumes
    # ------------------------------------------------------------------
    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_type",
            sa.Enum("PDF", "DOCX", "TXT", name="filetype"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("raw_text", sa.Text()),
        sa.Column("parsed_data", postgresql.JSONB()),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_resumes_candidate_id", "resumes", ["candidate_id"])
    op.execute("ALTER TABLE resumes ADD COLUMN embedding vector(1536)")

    # ------------------------------------------------------------------
    # skills
    # ------------------------------------------------------------------
    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100)),
    )
    op.create_index("ix_skills_name", "skills", ["name"], unique=True)

    # ------------------------------------------------------------------
    # candidate_skills  (junction table with extra columns)
    # ------------------------------------------------------------------
    op.create_table(
        "candidate_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proficiency_score", sa.Float()),
        sa.Column("years_experience", sa.Float()),
        sa.UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
    )
    op.create_index("ix_candidate_skills_candidate_id", "candidate_skills", ["candidate_id"])
    op.create_index("ix_candidate_skills_skill_id", "candidate_skills", ["skill_id"])

    # ------------------------------------------------------------------
    # interviews
    # ------------------------------------------------------------------
    op.create_table(
        "interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "resume_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resumes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "NOT_STARTED", "INTRODUCTION", "TECHNICAL",
                "FOLLOW_UP", "BEHAVIORAL", "FINALIZATION", "COMPLETED",
                name="interviewstatus",
            ),
            nullable=False,
            server_default="NOT_STARTED",
        ),
        sa.Column("skill_scores", postgresql.JSONB()),
        sa.Column("current_difficulty", sa.String(50)),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("overall_score", sa.Float()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_interviews_candidate_id", "interviews", ["candidate_id"])
    op.create_index("ix_interviews_job_id", "interviews", ["job_id"])
    op.create_index("ix_interviews_status", "interviews", ["status"])

    # ------------------------------------------------------------------
    # interview_questions
    # ------------------------------------------------------------------
    op.create_table(
        "interview_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "interview_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interview_questions.id"),
            nullable=True,
        ),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "TECHNICAL", "BEHAVIORAL", "SITUATIONAL", "FOLLOW_UP", "INTRODUCTION",
                name="questioncategory",
            ),
            nullable=False,
        ),
        sa.Column(
            "difficulty",
            sa.Enum("EASY", "MEDIUM", "HARD", name="questiondifficulty"),
            nullable=False,
        ),
        sa.Column("skill_tag", sa.String(100)),
        sa.Column("sequence_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_follow_up", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "asked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_interview_questions_interview_id", "interview_questions", ["interview_id"])
    op.create_index("ix_interview_questions_category", "interview_questions", ["category"])

    # ------------------------------------------------------------------
    # interview_answers
    # ------------------------------------------------------------------
    op.create_table(
        "interview_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interview_questions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_interview_answers_question_id", "interview_answers", ["question_id"], unique=True)

    # ------------------------------------------------------------------
    # evaluations
    # ------------------------------------------------------------------
    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "answer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interview_answers.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("technical_correctness", sa.Float()),
        sa.Column("relevance", sa.Float()),
        sa.Column("depth", sa.Float()),
        sa.Column("reasoning", sa.Float()),
        sa.Column("clarity", sa.Float()),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("feedback", sa.Text()),
        sa.Column("missing_concepts", postgresql.JSONB()),
        sa.Column("strengths", postgresql.JSONB()),
        sa.Column("weaknesses", postgresql.JSONB()),
    )
    op.create_index("ix_evaluations_answer_id", "evaluations", ["answer_id"], unique=True)

    # ------------------------------------------------------------------
    # conversation_messages
    # ------------------------------------------------------------------
    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "interview_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("SYSTEM", "AI", "CANDIDATE", name="messagerole"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_conversation_messages_interview_id", "conversation_messages", ["interview_id"])
    op.create_index("ix_conversation_messages_timestamp", "conversation_messages", ["timestamp"])

    # ------------------------------------------------------------------
    # interview_reports
    # ------------------------------------------------------------------
    op.create_table(
        "interview_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "interview_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interviews.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("overall_score", sa.Float()),
        sa.Column("technical_score", sa.Float()),
        sa.Column("behavioral_score", sa.Float()),
        sa.Column("summary", sa.Text()),
        sa.Column("strong_skills", postgresql.JSONB()),
        sa.Column("weak_skills", postgresql.JSONB()),
        sa.Column("recommendation", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_interview_reports_interview_id", "interview_reports", ["interview_id"], unique=True)

    # ------------------------------------------------------------------
    # recommendations
    # ------------------------------------------------------------------
    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("missing_skills", postgresql.JSONB()),
        sa.Column("learning_topics", postgresql.JSONB()),
        sa.Column("prerequisites", postgresql.JSONB()),
        sa.Column("practice_problems", postgresql.JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_recommendations_candidate_id", "recommendations", ["candidate_id"])

    # ------------------------------------------------------------------
    # knowledge_documents
    # ------------------------------------------------------------------
    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(512)),
    )
    op.create_index("ix_knowledge_documents_domain", "knowledge_documents", ["domain"])

    # ------------------------------------------------------------------
    # knowledge_chunks
    # ------------------------------------------------------------------
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN embedding vector(1536)")

    # ------------------------------------------------------------------
    # HNSW vector indexes for similarity search
    # ------------------------------------------------------------------
    op.execute(
        "CREATE INDEX ix_jobs_embedding_hnsw ON jobs"
        " USING hnsw (embedding vector_cosine_ops)"
        " WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX ix_resumes_embedding_hnsw ON resumes"
        " USING hnsw (embedding vector_cosine_ops)"
        " WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw ON knowledge_chunks"
        " USING hnsw (embedding vector_cosine_ops)"
        " WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    # Drop HNSW indexes first
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_resumes_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_jobs_embedding_hnsw")

    # Drop tables in reverse dependency order
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("recommendations")
    op.drop_table("interview_reports")
    op.drop_table("conversation_messages")
    op.drop_table("evaluations")
    op.drop_table("interview_answers")
    op.drop_table("interview_questions")
    op.drop_table("interviews")
    op.drop_table("candidate_skills")
    op.drop_table("skills")
    op.drop_table("resumes")
    op.drop_table("jobs")
    op.drop_table("candidate_profiles")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS messagerole")
    op.execute("DROP TYPE IF EXISTS questiondifficulty")
    op.execute("DROP TYPE IF EXISTS questioncategory")
    op.execute("DROP TYPE IF EXISTS interviewstatus")
    op.execute("DROP TYPE IF EXISTS filetype")
    op.execute("DROP TYPE IF EXISTS userrole")
