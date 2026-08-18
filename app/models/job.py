import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.interview import Interview



class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[list | None] = mapped_column(JSONB)
    preferred_skills: Mapped[list | None] = mapped_column(JSONB)
    responsibilities: Mapped[list | None] = mapped_column(JSONB)
    seniority: Mapped[str | None] = mapped_column(String(100))
    experience_years: Mapped[str | None] = mapped_column(String(50))
    education_requirement: Mapped[str | None] = mapped_column(String(255))
    technologies: Mapped[list | None] = mapped_column(JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    interviews: Mapped[list["Interview"]] = relationship(
        "Interview", back_populates="job"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title}>"
