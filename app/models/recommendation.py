import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile



class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    missing_skills: Mapped[list | None] = mapped_column(JSONB)
    learning_topics: Mapped[list | None] = mapped_column(JSONB)
    prerequisites: Mapped[list | None] = mapped_column(JSONB)
    practice_problems: Mapped[list | None] = mapped_column(JSONB)
    project_recommendations: Mapped[list | None] = mapped_column(JSONB)
    learning_sequence: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="recommendations"
    )

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} candidate_id={self.candidate_id}>"
