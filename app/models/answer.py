import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.question import InterviewQuestion
    from app.models.evaluation import Evaluation



class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    question: Mapped["InterviewQuestion"] = relationship(
        "InterviewQuestion", back_populates="answer"
    )
    evaluation: Mapped["Evaluation | None"] = relationship(
        "Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<InterviewAnswer id={self.id} question_id={self.question_id}>"
