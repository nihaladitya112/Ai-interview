import uuid

from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.answer import InterviewAnswer



class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_answers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    technical_correctness: Mapped[float | None] = mapped_column(Float)
    relevance: Mapped[float | None] = mapped_column(Float)
    depth: Mapped[float | None] = mapped_column(Float)
    reasoning: Mapped[float | None] = mapped_column(Float)
    clarity: Mapped[float | None] = mapped_column(Float)
    completeness: Mapped[float | None] = mapped_column(Float)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text)
    missing_concepts: Mapped[list | None] = mapped_column(JSONB)
    strengths: Mapped[list | None] = mapped_column(JSONB)
    weaknesses: Mapped[list | None] = mapped_column(JSONB)

    # Relationships
    answer: Mapped["InterviewAnswer"] = relationship(
        "InterviewAnswer", back_populates="evaluation"
    )

    def __repr__(self) -> str:
        return f"<Evaluation id={self.id} score={self.overall_score}>"
