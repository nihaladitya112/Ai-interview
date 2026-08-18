import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.interview import Interview
    from app.models.answer import InterviewAnswer



class QuestionCategory(str, enum.Enum):
    TECHNICAL = "TECHNICAL"
    BEHAVIORAL = "BEHAVIORAL"
    HR = "HR"
    PROJECT = "PROJECT"
    SITUATIONAL = "SITUATIONAL"
    PROBLEM_SOLVING = "PROBLEM_SOLVING"


class QuestionDifficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[QuestionCategory] = mapped_column(
        Enum(QuestionCategory, name="questioncategory"), nullable=False
    )
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        Enum(QuestionDifficulty, name="questiondifficulty"), nullable=False
    )
    skill_tag: Mapped[str | None] = mapped_column(String(100))
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_questions.id"), nullable=True
    )
    asked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    interview: Mapped["Interview"] = relationship(
        "Interview", back_populates="questions"
    )
    answer: Mapped["InterviewAnswer | None"] = relationship(
        "InterviewAnswer", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<InterviewQuestion id={self.id} category={self.category} difficulty={self.difficulty}>"
