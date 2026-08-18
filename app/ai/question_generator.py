"""
AI Question Generation Engine
==============================
Generates personalised, de-duplicated interview questions across all six
categories by filling rich template banks with data extracted from the
candidate's resume and the job description.

No external LLM API key is required for the base implementation. All
personalisation is achieved through slot-filling of structured templates
with the candidate's actual skills, projects, companies, and experience.

Deduplication is performed via cosine similarity on sentence-transformer
embeddings — any pair with similarity ≥ 0.85 is treated as a near-duplicate
and the lower-priority question is removed before saving.
"""

from __future__ import annotations

import random
import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json

from openai import AsyncOpenAI
from app.core.config import settings

from app.models.question import QuestionCategory, QuestionDifficulty
from app.schemas.questions import GeneratedQuestion

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Default difficulty distribution (sums to 1.0)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_DIFFICULTY_WEIGHTS: Dict[QuestionDifficulty, float] = {
    QuestionDifficulty.EASY:   0.20,
    QuestionDifficulty.MEDIUM: 0.40,
    QuestionDifficulty.HARD:   0.30,
    QuestionDifficulty.EXPERT: 0.10,
}

# Default category split for 30 questions buffer
DEFAULT_CATEGORY_COUNTS: Dict[QuestionCategory, int] = {
    QuestionCategory.TECHNICAL:      18,
    QuestionCategory.BEHAVIORAL:     8,
    QuestionCategory.PROJECT:        4,
    QuestionCategory.HR:             0,
    QuestionCategory.SITUATIONAL:    0,
    QuestionCategory.PROBLEM_SOLVING: 0,
}

DEDUP_THRESHOLD = 0.85


# ─────────────────────────────────────────────────────────────────────────────
# Candidate context dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CandidateContext:
    name: str = "the candidate"
    skills: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    experience_entries: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    education: List[str] = field(default_factory=list)
    companies: List[str] = field(default_factory=list)
    role: str = "Software Engineer"
    required_skills: List[str] = field(default_factory=list)
    experience_years: str = "some"
    seniority: str = "Mid-Level"

    @property
    def primary_skill(self) -> str:
        return self.skills[0] if self.skills else "software development"

    @property
    def primary_tech(self) -> str:
        return self.technologies[0] if self.technologies else self.primary_skill

    @property
    def primary_project(self) -> str:
        return self.projects[0] if self.projects else "your recent project"

    @property
    def primary_company(self) -> str:
        return self.companies[0] if self.companies else "your previous employer"

    @property
    def all_skills(self) -> List[str]:
        seen: set[str] = set()
        combined = []
        for s in (self.skills + self.technologies):
            if s.lower() not in seen:
                seen.add(s.lower())
                combined.append(s)
        return combined


def _extract_companies(experience_entries: List[str]) -> List[str]:
    """Pull company names from experience strings like 'SWE at Acme Corp (2020-2023)'."""
    companies: List[str] = []
    at_pattern = re.compile(r"\bat\s+([A-Z][A-Za-z0-9 &,.'-]+?)(?:\s*[\(\[]|\s*$)", re.MULTILINE)
    for entry in experience_entries:
        m = at_pattern.search(entry)
        if m:
            companies.append(m.group(1).strip())
    return companies or ["your previous employer"]


def build_context(resume_parsed: dict, job_dict: dict) -> CandidateContext:
    experience = resume_parsed.get("Experience", [])
    if isinstance(experience, str):
        experience = [experience]
    return CandidateContext(
        name=resume_parsed.get("Name", "the candidate"),
        skills=resume_parsed.get("Skills", []),
        technologies=resume_parsed.get("Technologies", []),
        experience_entries=experience,
        projects=resume_parsed.get("Projects", []),
        certifications=resume_parsed.get("Certifications", []),
        education=resume_parsed.get("Education", []),
        companies=_extract_companies(experience),
        role=job_dict.get("title", "Software Engineer"),
        required_skills=job_dict.get("required_skills", []),
        experience_years=job_dict.get("experience_years", "some"),
        seniority=job_dict.get("seniority", "Mid-Level"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Template banks (6 categories × 4 difficulties)
# Each template may use any CandidateContext attribute via {attr} slots.
# ─────────────────────────────────────────────────────────────────────────────

# Helper to pick N unique items from a list, with a fallback
def _pick(lst: list, n: int = 1, fallback: str = "this technology") -> list:
    return random.sample(lst, min(n, len(lst))) if lst else [fallback]


def _build_technical_templates(ctx: CandidateContext) -> Dict[QuestionDifficulty, List[str]]:
    """Generate exactly ONE question per unique skill from the resume."""
    skills = ctx.all_skills if ctx.all_skills else ["software development"]

    # Question templates that take a single skill. Each question is realistic
    # for a verbal interview (answerable in 1-2 minutes).
    question_patterns = [
        "What are the core concepts of {skill} that every developer should understand? Explain with examples from your experience.",
        "Can you explain how {skill} works internally at a high level? What are its strengths and weaknesses?",
        "Describe a challenging problem you solved using {skill}. What approach did you take?",
        "What are some common mistakes developers make when working with {skill}, and how do you avoid them?",
        "How does {skill} compare to its closest alternatives? When would you choose {skill} over them?",
        "What are the best practices you follow when working with {skill} in a team environment?",
        "Can you walk me through how you would set up a new project or module using {skill}?",
        "Explain the key design patterns or architectural principles you use when working with {skill}.",
        "What is your debugging approach when something goes wrong in a {skill} application?",
        "How do you ensure code quality and maintainability when working with {skill}?",
        "What recent updates or features in {skill} have you found most useful? Why?",
        "How would you explain {skill} to a junior developer who has never used it before?",
        "What are the performance considerations you keep in mind when using {skill}?",
        "How do you handle error handling and edge cases in {skill}?",
        "Describe how {skill} fits into a typical full-stack or end-to-end project architecture.",
    ]

    # Distribute questions across difficulties: cycle through skills
    easy_q, med_q, hard_q, expert_q = [], [], [], []
    buckets = [easy_q, med_q, hard_q, expert_q]

    for i, skill in enumerate(skills):
        pattern = question_patterns[i % len(question_patterns)]
        question = pattern.format(skill=skill)
        bucket = buckets[i % len(buckets)]
        bucket.append(question)

    # Ensure at least one question per difficulty level
    if not easy_q:
        easy_q.append(f"What are the fundamental concepts of {skills[0]} that you use daily?")
    if not med_q:
        med_q.append(f"Describe a real-world problem you solved using {skills[0]}.")
    if not hard_q:
        hard_q.append(f"How would you architect a scalable system using {skills[0]}?")
    if not expert_q:
        expert_q.append(f"What are the advanced optimisation techniques you've applied in {skills[0]}?")

    return {
        QuestionDifficulty.EASY: easy_q,
        QuestionDifficulty.MEDIUM: med_q,
        QuestionDifficulty.HARD: hard_q,
        QuestionDifficulty.EXPERT: expert_q,
    }


def _build_behavioral_templates(ctx: CandidateContext) -> Dict[QuestionDifficulty, List[str]]:
    proj = ctx.primary_project
    comp = ctx.primary_company
    return {
        QuestionDifficulty.EASY: [
            f"Tell me about a time at {comp} when you had to learn a new technology quickly. How did you approach it?",
            "Describe a situation where you disagreed with a team member. How did you resolve it?",
            "Give an example of when you had to manage competing priorities. What did you do?",
        ],
        QuestionDifficulty.MEDIUM: [
            f"Describe the most challenging bug you encountered in {proj}. How did you diagnose and fix it?",
            f"Tell me about a time when you had to deliver a project at {comp} under a very tight deadline. What sacrifices did you make?",
            "Describe a situation where you had to give critical feedback to a colleague. What was the outcome?",
            f"At {comp}, how did you handle a situation where the requirements changed significantly mid-project?",
        ],
        QuestionDifficulty.HARD: [
            f"Describe a major technical failure at {comp} that you were responsible for. How did you handle it and what did you learn?",
            "Tell me about a time you had to advocate for a technical decision that was unpopular. Were you successful?",
            f"Describe a situation where you had to rebuild trust with a stakeholder at {comp}. What happened?",
        ],
        QuestionDifficulty.EXPERT: [
            "Describe the most significant technical leadership challenge you've faced. What was the organisational impact?",
            f"Tell me about a time you had to balance technical debt against feature delivery at {comp}. How did you communicate this trade-off to non-technical stakeholders?",
        ],
    }


def _build_hr_templates(ctx: CandidateContext) -> Dict[QuestionDifficulty, List[str]]:
    role = ctx.role
    yrs = ctx.experience_years
    return {
        QuestionDifficulty.EASY: [
            f"Why are you interested in this {role} position specifically?",
            "Where do you see yourself in the next 3–5 years?",
            "What motivates you most in your day-to-day work?",
            "How do you stay current with industry trends and new technologies?",
        ],
        QuestionDifficulty.MEDIUM: [
            f"What does your ideal team look like for a {role} position, and how do you contribute to team culture?",
            "Describe your preferred working style — are you more independent or collaborative?",
            f"Given your {yrs} of experience, how have your career goals evolved?",
            "What is your approach to continuous learning and professional development?",
        ],
        QuestionDifficulty.HARD: [
            f"What is the biggest gap between your current skills and the requirements for this {role} role, and how do you plan to address it?",
            "If you could change one thing about your career trajectory, what would it be and why?",
        ],
        QuestionDifficulty.EXPERT: [
            "How do you measure your own success in a role, beyond standard performance metrics?",
            f"What would make you leave this {role} position within the first year?",
        ],
    }


def _build_project_templates(ctx: CandidateContext) -> Dict[QuestionDifficulty, List[str]]:
    proj = ctx.primary_project
    s = _pick(ctx.all_skills)
    s0 = s[0] if s else "your main technology"
    certs = ctx.certifications[0] if ctx.certifications else None
    return {
        QuestionDifficulty.EASY: [
            f"Your resume mentions a project called {proj}. Walk me through the architecture of it. What were the main components?",
            f"I noticed {proj} on your resume. What was your individual contribution, and how did you collaborate with the team?",
            f"Based on your resume, what tech stack did you choose for {proj} and why did you pick {s0}?",
        ],
        QuestionDifficulty.MEDIUM: [
            f"Regarding {proj} from your uploaded resume: What was the hardest technical problem you solved? How long did it take?",
            f"How did you test and ensure the quality of {proj}? What testing strategies did you use?",
            f"If you were to rebuild {proj} today with your current knowledge, what would you do differently?",
            f"In your resume you mention {proj}. How did you handle deployment and CI/CD for it?",
        ],
        QuestionDifficulty.HARD: [
            f"Describe the scalability challenges you faced in {proj} and how you designed around them.",
            f"What security considerations did you implement in {proj} based on your resume's tech stack? Were there any vulnerabilities you discovered?",
            *(
                [f"You hold a {certs} certification — how did the concepts from it influence the design of {proj}?"]
                if certs else
                [f"How did you measure the performance of {proj} in production?"]
            ),
        ],
        QuestionDifficulty.EXPERT: [
            f"How would you productionise {proj} for 10 million users? What would break first?",
            f"What was the most consequential architectural decision in {proj}, and were there better alternatives you considered?",
        ],
    }


def _build_situational_templates(ctx: CandidateContext) -> Dict[QuestionDifficulty, List[str]]:
    s0 = _pick(ctx.all_skills)[0] if ctx.all_skills else "your primary stack"
    role = ctx.role
    return {
        QuestionDifficulty.EASY: [
            f"If a junior developer asks you to review their {s0} code and it has multiple issues, how do you handle the feedback?",
            "You discover a small bug in production during a Friday evening release. What do you do?",
            "A product manager asks for a feature that you think is technically infeasible in the given timeline. How do you respond?",
        ],
        QuestionDifficulty.MEDIUM: [
            f"Imagine a critical {s0} service goes down and you're the only engineer available. Walk me through your incident response.",
            f"You're halfway through a feature sprint when you discover a security vulnerability in a dependency your {s0} app uses. What do you do?",
            f"A senior stakeholder insists on a technical approach you strongly disagree with for your {role} work. How do you handle it?",
            "Your team's velocity has dropped significantly. You're asked to investigate. What steps do you take?",
        ],
        QuestionDifficulty.HARD: [
            f"You've just joined a new company as a {role} and discover the codebase has significant technical debt with no documentation. What are your first 30 days?",
            f"A customer is experiencing a production issue that your {s0} team cannot reproduce. How do you investigate?",
            "You are asked to cut a feature mid-sprint to meet a business deadline. How do you decide what to cut?",
        ],
        QuestionDifficulty.EXPERT: [
            f"You are tasked with migrating a monolithic {s0} application to microservices with zero downtime. Describe your approach.",
            f"The company wants to adopt {s0} across teams, but there's resistance from senior engineers. How do you drive the change?",
        ],
    }


def _build_problem_solving_templates(ctx: CandidateContext) -> Dict[QuestionDifficulty, List[str]]:
    s0 = _pick(ctx.all_skills)[0] if ctx.all_skills else "Python"
    s1 = _pick(ctx.all_skills, 2)[-1] if len(ctx.all_skills) > 1 else s0
    return {
        QuestionDifficulty.EASY: [
            f"Given a list of integers in {s0}, how would you find the two numbers that sum to a target value?",
            "Explain the difference between BFS and DFS. When would you use each?",
            "How would you reverse a linked list? Walk me through the algorithm.",
        ],
        QuestionDifficulty.MEDIUM: [
            f"Design a simple in-memory key-value store with TTL support using {s0}.",
            f"In {s0}, implement a function to detect cycles in a directed graph.",
            "How would you implement a rate limiter that allows N requests per minute per user?",
            f"Design a URL shortener service. What data structures and storage would you use with {s1}?",
        ],
        QuestionDifficulty.HARD: [
            f"Design a distributed job scheduler using {s0}. How do you handle failures and ensure exactly-once execution?",
            "Given a stream of millions of events per second, how do you compute a sliding-window average with low latency?",
            f"Implement a least-recently-used (LRU) cache with O(1) get and put using {s0}.",
        ],
        QuestionDifficulty.EXPERT: [
            "Design Google's search autocomplete system. Discuss the data structures, consistency model, and latency requirements.",
            f"How would you design a real-time collaborative document editor (like Google Docs) using {s0} on the backend?",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Template registry
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_BUILDERS = {
    QuestionCategory.TECHNICAL:       _build_technical_templates,
    QuestionCategory.BEHAVIORAL:      _build_behavioral_templates,
    QuestionCategory.HR:              _build_hr_templates,
    QuestionCategory.PROJECT:         _build_project_templates,
    QuestionCategory.SITUATIONAL:     _build_situational_templates,
    QuestionCategory.PROBLEM_SOLVING: _build_problem_solving_templates,
}

SKILL_TAG_MAP: Dict[QuestionCategory, Optional[str]] = {
    QuestionCategory.TECHNICAL:       None,   # set per-question below
    QuestionCategory.BEHAVIORAL:      "soft-skills",
    QuestionCategory.HR:              "culture",
    QuestionCategory.PROJECT:         "project",
    QuestionCategory.SITUATIONAL:     "judgment",
    QuestionCategory.PROBLEM_SOLVING: "algorithms",
}


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication
# ─────────────────────────────────────────────────────────────────────────────

def _deduplicate(questions: List[GeneratedQuestion]) -> List[GeneratedQuestion]:
    """Remove near-duplicate questions using cosine similarity on embeddings."""
    if len(questions) <= 1:
        return questions

    try:
        from app.ai.matcher import embed
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]

        texts = [q.question_text for q in questions]
        vecs = embed(texts)
        sim_matrix = cosine_similarity(vecs)

        keep = [True] * len(questions)
        for i in range(len(questions)):
            if not keep[i]:
                continue
            for j in range(i + 1, len(questions)):
                if keep[j] and sim_matrix[i][j] >= DEDUP_THRESHOLD:
                    keep[j] = False

        return [q for q, k in zip(questions, keep) if k]

    except Exception as e:
        logger.warning(f"Deduplication skipped ({e}); returning all questions.")
        return questions


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def _difficulty_for_index(index: int, total: int, allowed: List[QuestionDifficulty]) -> QuestionDifficulty:
    """Distribute difficulties proportionally across the allowed set."""
    if len(allowed) == 1:
        return allowed[0]
    weights = [DEFAULT_DIFFICULTY_WEIGHTS.get(d, 0.25) for d in allowed]
    total_w = sum(weights)
    thresholds = []
    cumulative = 0.0
    for w in weights:
        cumulative += w / total_w
        thresholds.append(cumulative)
    ratio = (index + 0.5) / total
    for i, t in enumerate(thresholds):
        if ratio <= t:
            return allowed[i]
    return allowed[-1]


def _generate_questions_fallback(
    resume_parsed: dict,
    job_dict: dict,
    count: int = 5,
    categories: Optional[List[QuestionCategory]] = None,
    difficulties: Optional[List[QuestionDifficulty]] = None,
) -> List[GeneratedQuestion]:
    """
    Generate `count` personalised, de-duplicated interview questions.

    Args:
        resume_parsed: dict from Resume.parsed_data
        job_dict:      dict with job fields (required_skills, seniority, etc.)
        count:         total questions to generate
        categories:    subset of categories to use; None = all
        difficulties:  allowed difficulty levels; None = default distribution

    Returns:
        List of GeneratedQuestion, deduplicated and shuffled.
    """
    ctx = build_context(resume_parsed, job_dict)

    active_cats = categories or list(QuestionCategory)
    allowed_diffs = difficulties or list(QuestionDifficulty)

    # Build per-category question pools
    all_candidates: List[GeneratedQuestion] = []
    for cat in active_cats:
        builder = CATEGORY_BUILDERS[cat]
        template_bank = builder(ctx)

        for diff, templates in template_bank.items():
            if diff not in allowed_diffs:
                continue
            for text in templates:
                skill_tag = SKILL_TAG_MAP.get(cat)
                if cat == QuestionCategory.TECHNICAL and ctx.all_skills:
                    skill_tag = _pick(ctx.all_skills)[0].lower()
                all_candidates.append(GeneratedQuestion(
                    question_text=text,
                    category=cat,
                    difficulty=diff,
                    skill_tag=skill_tag,
                ))

    # Bypass deduplication for fallback templates to guarantee we meet the quota
    unique_candidates = all_candidates

    # Sample respecting category proportions
    random.shuffle(unique_candidates)

    # Build category quota
    raw_quota: Dict[QuestionCategory, int] = {}
    total_cat = len(active_cats)
    remaining = count
    for i, cat in enumerate(active_cats):
        if i == total_cat - 1:
            raw_quota[cat] = remaining
        else:
            default_frac = DEFAULT_CATEGORY_COUNTS.get(cat, 2) / sum(DEFAULT_CATEGORY_COUNTS.values())
            allotted = max(1, round(count * default_frac))
            raw_quota[cat] = allotted
            remaining -= allotted

    selected: List[GeneratedQuestion] = []
    for cat in active_cats:
        quota = raw_quota.get(cat, 1)
        pool = [q for q in unique_candidates if q.category == cat]
        # Apply difficulty distribution within the pool
        pool_by_diff: Dict[QuestionDifficulty, List[GeneratedQuestion]] = {}
        for q in pool:
            pool_by_diff.setdefault(q.difficulty, []).append(q)
        for i in range(quota):
            diff = _difficulty_for_index(i, quota, allowed_diffs)
            # Try the desired difficulty, fall back to any available
            bucket = pool_by_diff.get(diff, [])
            if not bucket:
                bucket = [q for d_list in pool_by_diff.values() for q in d_list]
            if not bucket:
                break
            chosen = bucket.pop(0)
            pool_by_diff[chosen.difficulty] = [q for q in pool_by_diff.get(chosen.difficulty, []) if q is not chosen]
            selected.append(chosen)

    random.shuffle(selected)
    return selected[:count]


async def generate_questions(
    resume_parsed: dict,
    job_dict: dict,
    count: int = 5,
    categories: Optional[List[QuestionCategory]] = None,
    difficulties: Optional[List[QuestionDifficulty]] = None,
    previous_questions: Optional[List[str]] = None,
) -> List[GeneratedQuestion]:
    """
    Generate `count` personalised interview questions using an LLM (Ollama or OpenAI).
    Falls back to template-based generation if LLM fails or is unconfigured.
    """
    api_key = settings.OPENAI_API_KEY or "ollama"
    
    if api_key.startswith("gsk_"):
        # Use Groq API
        base_url = "https://api.groq.com/openai/v1"
        model_name = "llama-3.1-70b-versatile"
    elif settings.OPENAI_API_KEY:
        # Use OpenAI API
        base_url = None
        model_name = "gpt-4o-mini"
    else:
        # Use local Ollama
        base_url = settings.OLLAMA_BASE_URL
        model_name = settings.OLLAMA_MODEL
    
    # Check if we should just use fallback directly
    if not settings.OPENAI_API_KEY and not settings.OLLAMA_BASE_URL:
        logger.warning("No LLM configured. Using fallback templates.")
        return _generate_questions_fallback(resume_parsed, job_dict, count, categories, difficulties)

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        ctx = build_context(resume_parsed, job_dict)
        
        active_cats = [c.value for c in (categories or list(QuestionCategory))]
        allowed_diffs = [d.value for d in (difficulties or list(QuestionDifficulty))]
        
        system_prompt = f"""You are an expert Technical Interviewer.
Your task is to generate {count} unique, non-repetitive interview questions for a candidate based on their resume.

CRITICAL INSTRUCTION 1: You MUST distribute the technical questions evenly across the DIFFERENT skills and technologies mentioned in the resume.
DO NOT ask multiple questions about the same technology (e.g., Kubernetes) if there are other technologies available. Ask exactly one question per technology until you have covered all of them.

CRITICAL INSTRUCTION 2: The questions MUST be realistic for a short, live verbal interview (answerable in 1-2 minutes).
DO NOT ask the candidate to build full applications or do project assignments (e.g., "Create a chatbot using Python", "Build a scraper"). 
Instead, ask targeted technical questions (e.g., "How does a dictionary work under the hood?", "What is the difference between X and Y?", "How do you handle rate limiting in X?").

Focus entirely on the technologies and projects explicitly mentioned below.
Return exactly {count} questions in a strict JSON array where each object has the following keys:
- "question_text" (string): The interview question itself.
- "category" (string): Must be one of {active_cats}.
- "difficulty" (string): Must be one of {allowed_diffs}.
- "skill_tag" (string): The primary technology or skill this question targets (e.g. "Python", "System Design", "Leadership").

Candidate Role: {ctx.role}
Experience: {ctx.experience_years}
Skills/Technologies: {", ".join(ctx.all_skills)}
Projects: {", ".join(ctx.projects)}

Ensure questions are highly varied across the different skills. Do not repeat the same concepts or same technology. Ensure valid JSON output.

IMPORTANT: To avoid repeating questions across different interviews, randomly select very specific, obscure, or creative angles for the questions. Do NOT just ask "What is X?" or "Explain Y". Think of highly specific scenarios.
"""

        if previous_questions:
            past_q_str = "\n".join(f"- {q}" for q in previous_questions)
            system_prompt += f"\n\nCRITICAL CONSTRAINT:\nThe candidate has already been asked the following questions in previous interviews. DO NOT generate these exact questions or extremely similar variations again. You MUST generate entirely new questions:\n{past_q_str}\n"

        import uuid
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate the interview questions in JSON format. Seed: {uuid.uuid4()}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.9
        )

        content = response.choices[0].message.content.strip()
        
        # Robustly extract JSON block if it's wrapped in markdown
        import re
        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
            
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            # If it failed to parse, it might be plain text that isn't wrapped in backticks
            # We will fallback to templates
            logger.error(f"Failed to parse JSON from LLM: {content[:200]}... Error: {e}")
            raise ValueError(f"Invalid JSON: {e}")
        
        # Handle cases where LLM returns a dictionary instead of an array
        if isinstance(data, dict):
            # Try to find a list inside the dict
            extracted_list = None
            for val in data.values():
                if isinstance(val, list):
                    extracted_list = val
                    break
            
            if extracted_list is not None:
                data = extracted_list
            else:
                # If no list found, it might be a single question object
                data = [data]
                
        if not isinstance(data, list):
            data = [data]
        
        questions = []
        for item in data:
            # If the model returned a list of strings instead of objects
            if isinstance(item, str):
                item = {
                    "question_text": item,
                    "category": "technical",
                    "difficulty": "medium",
                    "skill_tag": ""
                }
            
            if not isinstance(item, dict):
                continue
                
            try:
                # Map string values back to Enums
                cat_str = str(item.get("category")).lower()
                diff_str = str(item.get("difficulty")).lower()
                
                cat_val = next((c for c in QuestionCategory if c.value.lower() == cat_str), QuestionCategory.TECHNICAL)
                diff_val = next((d for d in QuestionDifficulty if d.value.lower() == diff_str), QuestionDifficulty.MEDIUM)
                
                q = GeneratedQuestion(
                    question_text=str(item.get("question_text")),
                    category=cat_val,
                    difficulty=diff_val,
                    skill_tag=str(item.get("skill_tag", ""))
                )
                questions.append(q)
            except Exception as e:
                logger.error(f"Failed to parse individual question: {e}")
                
        if len(questions) < 5:
            raise ValueError("LLM returned too few valid questions.")
            
        return questions[:count]

    except Exception as e:
        logger.error(f"LLM question generation failed: {e}. Falling back to templates.")
        return _generate_questions_fallback(resume_parsed, job_dict, count, categories, difficulties)
