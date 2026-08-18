import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Text, func, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.interview import Interview



class InterviewReport(Base):
    __tablename__ = "interview_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    overall_score: Mapped[float | None] = mapped_column(Float)
    technical_score: Mapped[float | None] = mapped_column(Float)
    behavioral_score: Mapped[float | None] = mapped_column(Float)
    problem_solving_score: Mapped[float | None] = mapped_column(Float)
    communication_score: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)
    strong_skills: Mapped[list | None] = mapped_column(JSONB)
    weak_skills: Mapped[list | None] = mapped_column(JSONB)
    technical_gaps: Mapped[list | None] = mapped_column(JSONB)
    best_answers: Mapped[list | None] = mapped_column(JSONB)
    weak_answers: Mapped[list | None] = mapped_column(JSONB)
    recommended_topics: Mapped[list | None] = mapped_column(JSONB)
    recommendation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    interview: Mapped["Interview"] = relationship(
        "Interview", back_populates="report"
    )

    def __repr__(self) -> str:
        return f"<InterviewReport id={self.id} interview_id={self.interview_id}>"
