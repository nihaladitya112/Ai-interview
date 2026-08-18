"""
Semantic Resume ↔ Job Matching Engine
======================================
Uses sentence-transformers (all-MiniLM-L6-v2) to embed skills and sections,
then computes cosine similarity for explainable, multi-dimensional match scoring.

Scoring weights:
  - Skill score:       55%
  - Experience score:  30%
  - Education score:   15%
"""

from __future__ import annotations

import re
import logging
from functools import lru_cache
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]

from app.schemas.match import MatchResult

logger = logging.getLogger(__name__)

SEMANTIC_MATCH_THRESHOLD = 0.65  # cosine similarity above this = skill "matched"

SKILL_WEIGHT = 0.55
EXPERIENCE_WEIGHT = 0.30
EDUCATION_WEIGHT = 0.15


# ─────────────────────────────────────────────────────────────────────────────
# Embedding model (loaded once, cached globally)
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_model():
    """Lazy-load the sentence-transformer model (cached after first call)."""
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformer model...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded.")
        return model
    except ImportError:
        logger.warning("sentence-transformers not installed — falling back to mock embeddings.")
        return None


def embed(texts: list[str]) -> np.ndarray:
    """Return (N, D) embedding matrix for a list of text strings."""
    model = _get_model()
    if model is None:
        # Deterministic random mock for testing without the heavy model
        rng = np.random.default_rng(seed=42)
        return rng.random((len(texts), 384)).astype(np.float32)
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)


# ─────────────────────────────────────────────────────────────────────────────
# Skill matching
# ─────────────────────────────────────────────────────────────────────────────

def semantic_skill_match(
    resume_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str] | None = None,
) -> tuple[float, list[str], list[str]]:
    """
    Compute semantic skill score.

    Returns:
        score         0–100
        matched       required skills semantically satisfied by the resume
        missing       required skills not satisfied
    """
    if not required_skills:
        return 100.0, [], []

    preferred_skills = preferred_skills or []
    all_job_skills = required_skills + preferred_skills

    # Encode all skill strings
    resume_vecs = embed([s.lower() for s in resume_skills]) if resume_skills else np.zeros((1, 384))
    job_vecs = embed([s.lower() for s in all_job_skills])

    # (n_job_skills, n_resume_skills) similarity matrix
    sim_matrix = cosine_similarity(job_vecs, resume_vecs)

    matched: list[str] = []
    missing: list[str] = []
    required_scores: list[float] = []

    for i, skill in enumerate(required_skills):
        best_sim = float(sim_matrix[i].max())
        required_scores.append(best_sim)
        if best_sim >= SEMANTIC_MATCH_THRESHOLD:
            matched.append(skill)
        else:
            missing.append(skill)

    # Preferred skills give a bonus (up to +10 points)
    preferred_bonus = 0.0
    if preferred_skills:
        pref_sims = []
        for i in range(len(required_skills), len(all_job_skills)):
            pref_sims.append(float(sim_matrix[i].max()))
        preferred_bonus = min(10.0, (sum(pref_sims) / len(pref_sims)) * 10.0)

    base_score = (sum(required_scores) / len(required_scores)) * 100.0
    skill_score = min(100.0, base_score + preferred_bonus)

    return round(skill_score, 1), matched, missing


# ─────────────────────────────────────────────────────────────────────────────
# Experience scoring
# ─────────────────────────────────────────────────────────────────────────────

def _extract_years(text: str) -> Optional[float]:
    """Pull the first number of years from a string like '3+ years' or '2-4 years'."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*years?", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def score_experience(resume_experience: list[str], required_years_str: str) -> float:
    """
    Score candidate experience vs. required years.

    Strategy:
      - Count jobs/roles mentioned in experience list as a proxy for years.
      - If the JD specifies '3+ years', score scales from 0 (0 yrs) to 100 (≥required).
    """
    required_years = _extract_years(required_years_str or "") or 2.0

    # Estimate candidate years: each experience entry ≈ assume average 1.5 yrs
    # But try to extract explicit year ranges first (e.g. "2020-2023" = 3 yrs)
    candidate_years = 0.0
    for exp in resume_experience:
        # Try "YYYY-YYYY" pattern
        span = re.findall(r"\b(20\d{2}|19\d{2})\b", exp)
        if len(span) >= 2:
            years = abs(int(span[-1]) - int(span[0]))
            candidate_years += years
        elif len(span) == 1:
            # Ongoing role: assume present year
            from datetime import datetime
            candidate_years += datetime.now().year - int(span[0])
        else:
            candidate_years += 1.5  # fallback estimate

    # Soft-ceiling scoring: full marks at required, graceful decay below
    if candidate_years >= required_years:
        score = 100.0
    else:
        score = (candidate_years / required_years) * 100.0

    return round(min(100.0, score), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Education scoring
# ─────────────────────────────────────────────────────────────────────────────

def score_education(resume_education: list[str], required_edu: str) -> float:
    """
    Semantic similarity between candidate's highest education and the job requirement.
    """
    if not required_edu or not resume_education:
        return 75.0  # neutral when data is missing

    resume_edu_text = " ".join(resume_education)
    vecs = embed([resume_edu_text.lower(), required_edu.lower()])
    sim = float(cosine_similarity([vecs[0]], [vecs[1]])[0][0])
    return round(min(100.0, sim * 100.0), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Strength / weakness generation
# ─────────────────────────────────────────────────────────────────────────────

def _generate_narrative(
    skill_score: float,
    experience_score: float,
    education_score: float,
    matched: list[str],
    missing: list[str],
) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    weaknesses: list[str] = []

    if skill_score >= 80:
        strengths.append(f"Strong technical skills — {len(matched)} of the required skills are a match.")
    elif skill_score >= 60:
        strengths.append(f"Partial skill overlap — {len(matched)} required skill(s) covered.")
    else:
        weaknesses.append("Limited skill alignment with the job requirements.")

    if missing:
        weaknesses.append(f"Missing key required skills: {', '.join(missing[:5])}.")

    if experience_score >= 90:
        strengths.append("Experience level meets or exceeds the role requirements.")
    elif experience_score >= 60:
        strengths.append("Candidate has relevant experience, though slightly below the ideal range.")
    else:
        weaknesses.append("Experience level appears below what this role requires.")

    if education_score >= 80:
        strengths.append("Educational background aligns well with the job requirement.")
    elif education_score < 50:
        weaknesses.append("Education background may not fully match the stated requirement.")

    return strengths, weaknesses


# ─────────────────────────────────────────────────────────────────────────────
# Main entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def match_resume_to_job(resume_parsed: dict, job_parsed: dict) -> MatchResult:
    """
    Run the full matching pipeline and return a MatchResult.

    Args:
        resume_parsed: parsed_data dict from the Resume model
        job_parsed:    dict with keys matching the Job model fields
    """
    resume_skills: list[str] = resume_parsed.get("Skills", []) + resume_parsed.get("Technologies", [])
    required_skills: list[str] = job_parsed.get("required_skills") or []
    preferred_skills: list[str] = job_parsed.get("preferred_skills") or []

    skill_score, matched_skills, missing_skills = semantic_skill_match(
        resume_skills, required_skills, preferred_skills
    )

    resume_experience: list[str] = resume_parsed.get("Experience", [])
    required_years_str: str = job_parsed.get("experience_years") or ""
    experience_score = score_experience(resume_experience, required_years_str)

    resume_education: list[str] = resume_parsed.get("Education", [])
    required_edu: str = job_parsed.get("education_requirement") or ""
    education_score = score_education(resume_education, required_edu)

    overall_score = round(
        SKILL_WEIGHT * skill_score
        + EXPERIENCE_WEIGHT * experience_score
        + EDUCATION_WEIGHT * education_score,
        1,
    )

    strengths, weaknesses = _generate_narrative(
        skill_score, experience_score, education_score, matched_skills, missing_skills
    )

    return MatchResult(
        overall_score=overall_score,
        skill_score=skill_score,
        experience_score=experience_score,
        education_score=education_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        strengths=strengths,
        weaknesses=weaknesses,
    )
