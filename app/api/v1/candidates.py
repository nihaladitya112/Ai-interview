import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.recommendation import Recommendation
from app.models.skill import CandidateSkill, Skill
from app.schemas.recommendation import RecommendationResponse
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/candidates", tags=["candidates"])


class SkillResponse(BaseModel):
    skill_id: uuid.UUID
    name: str
    category: str
    proficiency_score: float

    model_config = ConfigDict(from_attributes=True)


@router.get("/{id}/skills", response_model=List[SkillResponse])
async def get_candidate_skills(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve candidate skills and proficiency scores.
    """
    # Verify candidate exists
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Fetch skills
    query = (
        select(CandidateSkill, Skill)
        .join(Skill, CandidateSkill.skill_id == Skill.id)
        .where(CandidateSkill.candidate_id == id)
    )
    result = await db.execute(query)
    
    response = []
    for cand_skill, skill in result.all():
        response.append(
            SkillResponse(
                skill_id=skill.id,
                name=skill.name,
                category=skill.category,
                proficiency_score=cand_skill.proficiency_score
            )
        )
        
    return response


@router.get("/{id}/recommendations", response_model=List[RecommendationResponse])
async def get_candidate_recommendations(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve learning recommendations for a candidate.
    """
    query = select(Recommendation).where(Recommendation.candidate_id == id)
    result = await db.execute(query)
    recommendations = result.scalars().all()
    
    return recommendations
