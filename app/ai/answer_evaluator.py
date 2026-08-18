"""
Answer Evaluator
================
Mock implementation of answer evaluation. Scores answers on five dimensions
and generates human-readable feedback.

In production, this would call an LLM with a structured evaluation prompt.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import List

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
    """
    Simulates structured JSON output from an LLM on a 0-10 scale.
    """
    import hashlib
    h = int(hashlib.md5((answer_text + question_text).encode()).hexdigest()[:8], 16)
    
    # Generate some random-ish but deterministic scores between 4.0 and 9.5
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


def evaluate_answer(
    question_text: str,
    answer_text: str,
    skill_tag: str | None = None,
    category: str = "TECHNICAL",
    rag_context: str | None = None,
) -> EvaluationResult:
    """
    Evaluate an answer using a mock LLM returning structured JSON,
    then apply deterministic rules to adjust the scores.
    """
    # 1. Get LLM structured output
    llm_output = _mock_llm_evaluate(question_text, answer_text, skill_tag)
    
    # Extract raw scores
    tech = llm_output["technical_correctness"]
    rel = llm_output["relevance"]
    dep = llm_output["depth"]
    res = llm_output["reasoning"]
    clr = llm_output["clarity"]
    comp = llm_output["completeness"]
    
    feedback = llm_output["feedback"]
    strengths = llm_output["strengths"]
    weaknesses = llm_output["weaknesses"]
    missing = llm_output["missing_concepts"]

    # 2. Deterministic Rule Overrides (Do not blindly trust the LLM)
    word_count = len(answer_text.split())
    
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
        # Check if the candidate's core answer words appear in the truth context
        ans_core = answer_lower - stopwords
        if ans_core and len(ans_core & rag_lower) / len(ans_core) < 0.15:
            # Answer deviates heavily from the ground truth RAG context
            tech = min(tech, 3.5)
            comp = min(comp, 4.0)
            weaknesses.append("Answer contradicts or misses the core technical knowledge base.")
            
    # Rule D: Sanity check overall score
    overall = round((tech*0.25 + rel*0.20 + dep*0.15 + res*0.15 + clr*0.10 + comp*0.15), 1)

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
