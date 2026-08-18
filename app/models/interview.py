import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile
    from app.models.job import Job
    from app.models.question import InterviewQuestion
    from app.models.report import InterviewReport



class InterviewStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    INTRODUCTION = "INTRODUCTION"
    TECHNICAL = "TECHNICAL"
    FOLLOW_UP = "FOLLOW_UP"
    BEHAVIORAL = "BEHAVIORAL"
    FINALIZATION = "FINALIZATION"
    COMPLETED = "COMPLETED"


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interviewstatus"),
        nullable=False,
        default=InterviewStatus.NOT_STARTED,
        index=True,
    )
    # Tracks per-skill performance scores as dict e.g. {"python": 8.5, "sql": 6.1}
    skill_scores: Mapped[dict | None] = mapped_column(JSONB)
    current_difficulty: Mapped[str | None] = mapped_column()
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="interviews"
    )
    job: Mapped["Job"] = relationship("Job", back_populates="interviews")
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        "InterviewQuestion", back_populates="interview", cascade="all, delete-orphan"
    )
    conversation_messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="interview", cascade="all, delete-orphan"
    )
    report: Mapped["InterviewReport | None"] = relationship(
        "InterviewReport", back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Interview id={self.id} status={self.status}>"


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    class MessageRole(str, enum.Enum):
        SYSTEM = "SYSTEM"
        AI = "AI"
        CANDIDATE = "CANDIDATE"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="messagerole"), nullable=False
    )
    content: Mapped[str] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    interview: Mapped["Interview"] = relationship(
        "Interview", back_populates="conversation_messages"
    )

    def __repr__(self) -> str:
        return f"<ConversationMessage id={self.id} role={self.role}>"
