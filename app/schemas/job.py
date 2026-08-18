from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime

class JobCreate(BaseModel):
    title: str
    company: Optional[str] = None
    description: str

class JobResponse(BaseModel):
    id: uuid.UUID
    title: str
    company: Optional[str] = None
    description: str
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    seniority: Optional[str] = None
    experience_years: Optional[str] = None
    education_requirement: Optional[str] = None
    technologies: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
