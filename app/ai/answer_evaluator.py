"""
Answer Evaluator
================
Implementation of answer evaluation using LLMs. Scores answers on five dimensions
and generates human-readable feedback.
"""
from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field
from typing import List

from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    technical_correctness: float = 0.0
    relevance: float = 0.0
    depth: float = 0.0
    reasoning: float = 0.0
    clarity: float = 0.0
    completeness: float = 0.0
    overall_score: float = 0.0
    feedback: str = ""
    missing_concepts: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


def _mock_llm_evaluate(
    question_text: str, answer_text: str, skill_tag: str | None
) -> dict:
    """Fallback if no LLM is configured."""
    import hashlib
    h = int(hashlib.md5((answer_text + question_text).encode()).hexdigest()[:8], 16)
    
    def _score(offset: int) -> float:
        return 4.0 + ((h + offset) % 55) / 10.0

    tech = _score(1)
    rel = _score(2)
    dep = _score(3)
    res = _score(4)
    clr = _score(5)
    comp = _score(6)
    
    overall = round((tech*0.25 + rel*0.20 + dep*0.15 + res*0.15 + clr*0.10 + comp*0.15), 1)

    return {
        "technical_correctness": tech,
        "relevance": rel,
        "depth": dep,
        "reasoning": res,
        "clarity": clr,
        "completeness": comp,
        "overall_score": overall,
        "feedback": "This is a simulated LLM feedback.",
        "missing_concepts": [f"Deep dive into {skill_tag or 'fundamentals'}"] if overall < 7.0 else [],
        "strengths": ["Clear explanation."] if clr >= 7.0 else [],
        "weaknesses": ["Lacks detail."] if dep < 6.0 else []
    }


async def _llm_evaluate(
    question_text: str, answer_text: str, skill_tag: str | None
) -> dict:
    """Evaluate using the configured LLM."""
    api_key = settings.OPENAI_API_KEY or "ollama"
    
    if api_key.startswith("gsk_"):
        base_url = "https://api.groq.com/openai/v1"
        model_name = "openai/gpt-oss-120b"
    elif settings.OPENAI_API_KEY:
        base_url = None
        model_name = "gpt-4o-mini"
    else:
        base_url = settings.OLLAMA_BASE_URL
        model_name = settings.OLLAMA_MODEL
        
    if not settings.OPENAI_API_KEY and not settings.OLLAMA_BASE_URL:
        return _mock_llm_evaluate(question_text, answer_text, skill_tag)
        
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    system_prompt = f"""You are an expert technical interviewer evaluating a candidate's answer.
Question: "{question_text}"
Skill/Topic: {skill_tag or 'General'}

Evaluate the following candidate's answer on a scale of 0.0 to 10.0 for the following metrics:
- technical_correctness (is the technical info accurate?)
- relevance (does it answer the question directly?)
- depth (does it go beyond surface level?)
- reasoning (is the logic sound?)
- clarity (is the communication clear?)
- completeness (are all parts of the question addressed?)

Also provide:
- feedback: a short, constructive paragraph for the candidate
- missing_concepts: list of up to 3 technical concepts they failed to mention
- strengths: list of up to 2 things they did well
- weaknesses: list of up to 2 areas for improvement

Return EXACTLY a JSON object with the following keys: "technical_correctness", "relevance", "depth", "reasoning", "clarity", "completeness", "feedback", "missing_concepts", "strengths", "weaknesses"
Do not include any other text outside the JSON.
"""

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Candidate Answer: \"{answer_text}\"\nEvaluate the answer."}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        
        # Calculate overall score
        tech = float(data.get("technical_correctness", 0.0))
        rel = float(data.get("relevance", 0.0))
        dep = float(data.get("depth", 0.0))
        res = float(data.get("reasoning", 0.0))
        clr = float(data.get("clarity", 0.0))
        comp = float(data.get("completeness", 0.0))
        
        overall = round((tech*0.25 + rel*0.20 + dep*0.15 + res*0.15 + clr*0.10 + comp*0.15), 1)
        data["overall_score"] = overall
        
        # Ensure array fields exist
        data["missing_concepts"] = data.get("missing_concepts") or []
        data["strengths"] = data.get("strengths") or []
        data["weaknesses"] = data.get("weaknesses") or []
        data["feedback"] = data.get("feedback") or "No detailed feedback provided."
        
        return data
    except Exception as e:
        logger.error(f"LLM evaluation failed: {e}. Falling back to mock evaluator.")
        return _mock_llm_evaluate(question_text, answer_text, skill_tag)


async def evaluate_answer(
    question_text: str,
    answer_text: str,
    skill_tag: str | None = None,
    category: str = "TECHNICAL",
    rag_context: str | None = None,
) -> EvaluationResult:
    """
    Evaluate an answer using an LLM returning structured JSON,
    then apply deterministic rules to adjust the scores.
    """
    # 0. Check for empty or skipped answers
    word_count = len(answer_text.strip().split())
    answer_clean = answer_text.strip().lower().replace(".", "").replace(",", "")
    skip_phrases = ["skip", "i don't know", "i dont know", "pass", "next", "skipped by candidate"]
    
    if word_count < 3 or answer_clean in skip_phrases:
        return EvaluationResult(
            technical_correctness=0.0,
            relevance=0.0,
            depth=0.0,
            reasoning=0.0,
            clarity=0.0,
            completeness=0.0,
            overall_score=0.0,
            feedback="The question was skipped or the answer was too short to evaluate.",
            weaknesses=["Did not attempt to answer the question."]
        )

    # 1. Get LLM structured output
    llm_output = await _llm_evaluate(question_text, answer_text, skill_tag)
    
    # Extract raw scores
    tech = float(llm_output.get("technical_correctness", 0.0))
    rel = float(llm_output.get("relevance", 0.0))
    dep = float(llm_output.get("depth", 0.0))
    res = float(llm_output.get("reasoning", 0.0))
    clr = float(llm_output.get("clarity", 0.0))
    comp = float(llm_output.get("completeness", 0.0))
    
    feedback = str(llm_output.get("feedback", ""))
    strengths = list(llm_output.get("strengths", []))
    weaknesses = list(llm_output.get("weaknesses", []))
    missing = list(llm_output.get("missing_concepts", []))

    # 2. Deterministic Rule Overrides
    
    # Rule A: Extreme length penalty
    if word_count < 10:
        dep = min(dep, 4.0)
        comp = min(comp, 3.5)
        rel = min(rel, 5.0)
        weaknesses.append("Response is far too short to be fully evaluated.")
        
    # Rule B: Keyword validation
    answer_lower = set(answer_text.lower().split())
    question_lower = set(question_text.lower().split())
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to",
                 "for", "of", "and", "or", "but", "not", "with", "this", "that", "it",
                 "i", "you", "we", "how", "what", "when", "where", "why", "do", "does"}
    q_keywords = question_lower - stopwords
    
    overlap = len(answer_lower & q_keywords) / max(len(q_keywords), 1)
    if overlap < 0.2 and word_count >= 10:
        # Long answer but misses question keywords entirely
        rel = min(rel, 4.5)
        tech = min(tech, 5.5)
        weaknesses.append("Answer does not address the core keywords of the question.")

    # Rule C: RAG Context Verification
    if rag_context:
        rag_lower = set(rag_context.lower().split()) - stopwords
        ans_core = answer_lower - stopwords
        if ans_core and len(ans_core & rag_lower) / len(ans_core) < 0.15:
            tech = min(tech, 3.5)
            comp = min(comp, 4.0)
            weaknesses.append("Answer contradicts or misses the core technical knowledge base.")
            
    # Rule D: Sanity check overall score
    overall = round((tech*0.25 + rel*0.20 + dep*0.15 + res*0.15 + clr*0.10 + comp*0.15), 1)

    # Adjust feedback if it wasn't provided well
    if not feedback or feedback == "No detailed feedback provided.":
        if overall >= 8.5:
            feedback = "Excellent, highly detailed answer."
        elif overall >= 6.0:
            feedback = "Good answer, but could be improved."
        else:
            feedback = "The answer needs more development and clarity."

    return EvaluationResult(
        technical_correctness=tech,
        relevance=rel,
        depth=dep,
        reasoning=res,
        clarity=clr,
        completeness=comp,
        overall_score=overall,
        feedback=feedback,
        missing_concepts=missing,
        strengths=strengths,
        weaknesses=list(set(weaknesses)),  # dedup
    )
