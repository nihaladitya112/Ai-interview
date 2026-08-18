"""
Interview Engine — State Machine
=================================
Orchestrates the full interview lifecycle:

  NOT_STARTED → INTRODUCTION → TECHNICAL ⇄ FOLLOW_UP → BEHAVIORAL → FINALIZATION → COMPLETED

Maintains per-session context (conversation history, per-skill scores,
adaptive difficulty, questions asked) and persists state to the database.
"""
from __future__ import annotations

import uuid
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.interview import Interview, InterviewStatus, ConversationMessage
from app.models.question import InterviewQuestion, QuestionCategory, QuestionDifficulty
from app.models.answer import InterviewAnswer
from app.models.evaluation import Evaluation
from app.ai.answer_evaluator import evaluate_answer, EvaluationResult
from app.ai.rag_service import retrieve_context
from app.schemas.interview import (
    CurrentQuestionInfo,
    InterviewStateResponse,
    AnswerEvaluationResponse,
    SubmitAnswerResponse,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

TECHNICAL_QUOTA = 9       # questions in TECHNICAL phase
BEHAVIORAL_QUOTA = 4      # questions in BEHAVIORAL phase
FINALIZATION_QUOTA = 2    # questions in FINALIZATION phase
FOLLOW_UP_THRESHOLD = 4.5 # score below this → generate a follow-up
DIFFICULTY_UP_THRESHOLD = 8.5
DIFFICULTY_DOWN_THRESHOLD = 4.0
RECENT_WINDOW = 3         # last N scores for adaptive difficulty

DIFFICULTY_ORDER = [
    QuestionDifficulty.EASY,
    QuestionDifficulty.MEDIUM,
    QuestionDifficulty.HARD,
    QuestionDifficulty.EXPERT,
]


# ─────────────────────────────────────────────────────────────────────────────
# In-memory session cache (per interview_id)
# ─────────────────────────────────────────────────────────────────────────────

class InterviewSession:
    """Tracks in-memory state for an active interview."""

    def __init__(self, interview_id: uuid.UUID) -> None:
        self.interview_id = interview_id
        self.current_difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM
        self.questions_asked: List[uuid.UUID] = []
        self.skills_tested: Set[str] = set()
        self.recent_scores: deque[float] = deque(maxlen=RECENT_WINDOW)
        self.skill_scores: Dict[str, List[float]] = {}   # skill → list of scores
        self.consecutive_weaknesses: Dict[str, int] = {} # skill -> count
        self.current_question_id: Optional[uuid.UUID] = None
        self.phase_question_count: int = 0   # questions asked in the current phase
        self.in_follow_up: bool = False

    def record_and_adapt(self, eval_result: EvaluationResult, skill_tag: str | None) -> None:
        score = eval_result.overall_score
        self.recent_scores.append(score)
        if skill_tag:
            self.skill_scores.setdefault(skill_tag, []).append(score)
            self.skills_tested.add(skill_tag)
            
            if score <= 4.0:
                self.consecutive_weaknesses[skill_tag] = self.consecutive_weaknesses.get(skill_tag, 0) + 1
            elif score >= 6.0:
                self.consecutive_weaknesses[skill_tag] = 0

        idx = DIFFICULTY_ORDER.index(self.current_difficulty)
        if score >= 8.5 and idx < len(DIFFICULTY_ORDER) - 1:
            self.current_difficulty = DIFFICULTY_ORDER[idx + 1]
            logger.info(f"Difficulty ↑ to {self.current_difficulty.value} (Strong answer)")
        elif score <= 4.0 and idx > 0:
            self.current_difficulty = DIFFICULTY_ORDER[idx - 1]
            logger.info(f"Difficulty ↓ to {self.current_difficulty.value} (Weak answer)")

    @property
    def avg_recent(self) -> float:
        return sum(self.recent_scores) / len(self.recent_scores) if self.recent_scores else 50.0

    @property
    def aggregated_skill_scores(self) -> Dict[str, float]:
        return {
            skill: round(sum(scores) / len(scores), 1)
            for skill, scores in self.skill_scores.items()
        }


# Global session store (in production, use Redis or similar)
_sessions: Dict[uuid.UUID, InterviewSession] = {}


def _get_session(interview_id: uuid.UUID) -> InterviewSession:
    if interview_id not in _sessions:
        _sessions[interview_id] = InterviewSession(interview_id)
    return _sessions[interview_id]


# ─────────────────────────────────────────────────────────────────────────────
# Helper: pick the next question from the pre-generated pool
# ─────────────────────────────────────────────────────────────────────────────

async def _pick_next_question(
    interview_id: uuid.UUID,
    session: InterviewSession,
    target_category: QuestionCategory,
    db: AsyncSession,
    is_follow_up: bool = False,
    force_difficulty: QuestionDifficulty | None = None,
) -> InterviewQuestion | None:
    """Select the next un-asked question matching the target category and difficulty."""
    asked_ids = session.questions_asked

    query = (
        select(InterviewQuestion)
        .where(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.category == target_category,
        )
        .order_by(InterviewQuestion.sequence_number)
    )
    result = await db.execute(query)
    candidates = result.scalars().all()

    # Prefer the current difficulty, fall back to any available
    target_diff = force_difficulty or session.current_difficulty
    preferred = [q for q in candidates if q.id not in asked_ids and q.difficulty == target_diff]
    fallback = [q for q in candidates if q.id not in asked_ids]

    chosen = (preferred or fallback)
    if not chosen:
        return None

    question = chosen[0]
    session.questions_asked.append(question.id)
    session.current_question_id = question.id
    session.in_follow_up = is_follow_up
    return question


def _question_to_info(q: InterviewQuestion) -> CurrentQuestionInfo:
    return CurrentQuestionInfo(
        question_id=str(q.id),
        question_text=q.question_text,
        category=q.category,
        difficulty=q.difficulty,
        skill_tag=q.skill_tag,
        sequence_number=q.sequence_number,
    )


async def _add_conversation_message(
    interview_id: uuid.UUID,
    role: str,
    content: str,
    db: AsyncSession,
) -> None:
    msg = ConversationMessage(
        id=uuid.uuid4(),
        interview_id=interview_id,
        role=ConversationMessage.MessageRole(role),
        content=content,
    )
    db.add(msg)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def start_interview(interview_id: uuid.UUID, db: AsyncSession) -> InterviewStateResponse:
    """Transition NOT_STARTED → INTRODUCTION → TECHNICAL and serve the first question."""
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        raise ValueError("Interview not found")
    if interview.status != InterviewStatus.NOT_STARTED:
        raise ValueError(f"Interview already in state {interview.status.value}")

    session = _get_session(interview_id)

    # INTRODUCTION phase: record a system greeting
    interview.status = InterviewStatus.INTRODUCTION
    interview.started_at = datetime.now(timezone.utc)
    await _add_conversation_message(
        interview_id, "SYSTEM",
        "Welcome to your AI-powered interview session. Let's begin with some technical questions.",
        db,
    )

    # Immediately transition to TECHNICAL and serve first question
    interview.status = InterviewStatus.TECHNICAL
    first_q = await _pick_next_question(interview_id, session, QuestionCategory.TECHNICAL, db)

    current_q_info: CurrentQuestionInfo | None = None
    if first_q:
        current_q_info = _question_to_info(first_q)
        await _add_conversation_message(interview_id, "AI", first_q.question_text, db)
        session.phase_question_count = 1

    await db.commit()

    return InterviewStateResponse(
        interview_id=str(interview_id),
        status=interview.status,
        current_question=current_q_info,
        current_difficulty=session.current_difficulty.value,
        questions_asked=len(session.questions_asked),
        total_questions=interview.total_questions,
        skill_scores=session.aggregated_skill_scores,
        overall_score=None,
        conversation_history=[],
    )


async def submit_answer(
    interview_id: uuid.UUID,
    answer_text: str,
    db: AsyncSession,
) -> SubmitAnswerResponse:
    """Process a candidate answer: evaluate, persist, determine next action."""
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        raise ValueError("Interview not found")
    if interview.status == InterviewStatus.COMPLETED:
        raise ValueError("Interview is already completed")

    session = _get_session(interview_id)
    if not session.current_question_id:
        raise ValueError("No current question to answer")

    # ── Fetch the current question ──
    q_result = await db.execute(
        select(InterviewQuestion).where(InterviewQuestion.id == session.current_question_id)
    )
    question = q_result.scalar_one_or_none()
    if not question:
        raise ValueError("Current question not found in database")

    # ── Record the answer ──
    answer_obj = InterviewAnswer(
        id=uuid.uuid4(),
        question_id=question.id,
        answer_text=answer_text,
    )
    db.add(answer_obj)
    await _add_conversation_message(interview_id, "CANDIDATE", answer_text, db)

    # ── RAG Verification ──
    rag_context = None
    if question.category == QuestionCategory.TECHNICAL:
        # Retrieve relevant context from knowledge base
        chunks = await retrieve_context(db, query=answer_text, domain=question.skill_tag, limit=2)
        if chunks:
            rag_context = "\n".join([c.content for c in chunks])

    # ── Evaluate ──
    eval_result: EvaluationResult = evaluate_answer(
        question_text=question.question_text,
        answer_text=answer_text,
        skill_tag=question.skill_tag,
        category=question.category.value,
        rag_context=rag_context
    )

    eval_obj = Evaluation(
        id=uuid.uuid4(),
        answer_id=answer_obj.id,
        technical_correctness=eval_result.technical_correctness,
        relevance=eval_result.relevance,
        depth=eval_result.depth,
        reasoning=eval_result.reasoning,
        clarity=eval_result.clarity,
        completeness=eval_result.completeness,
        overall_score=eval_result.overall_score,
        feedback=eval_result.feedback,
        missing_concepts=eval_result.missing_concepts,
        strengths=eval_result.strengths,
        weaknesses=eval_result.weaknesses,
    )
    db.add(eval_obj)

    # ── Update session ──
    session.record_and_adapt(eval_result, question.skill_tag)

    # ── Determine next action ──
    next_question: InterviewQuestion | None = None
    message = ""

    if interview.status == InterviewStatus.FINALIZATION:
        if session.phase_question_count >= FINALIZATION_QUOTA:
            # We're wrapping up
            interview.status = InterviewStatus.COMPLETED
            interview.completed_at = datetime.now(timezone.utc)
            interview.skill_scores = session.aggregated_skill_scores
            interview.overall_score = round(
                sum(s for scores in session.skill_scores.values() for s in scores)
                / max(sum(len(v) for v in session.skill_scores.values()), 1),
                1,
            )
            message = "Interview completed. Thank you for your time!"
            await _add_conversation_message(interview_id, "SYSTEM", message, db)
        else:
            next_question = await _pick_next_question(
                interview_id, session, QuestionCategory.PROJECT, db
            )
            if next_question:
                session.phase_question_count += 1
            message = "One final question about your project."

    elif interview.status in (InterviewStatus.TECHNICAL, InterviewStatus.FOLLOW_UP):
        force_diff = None
        if question.skill_tag and session.consecutive_weaknesses.get(question.skill_tag, 0) >= 2:
            force_diff = QuestionDifficulty.EASY
            # reset to avoid getting stuck if we pick a different skill next
            session.consecutive_weaknesses[question.skill_tag] = 0

        # Check if we should do a follow-up
        is_incomplete = (4.0 < eval_result.overall_score < 7.0) or eval_result.depth < 5.0

        if (
            not session.in_follow_up
            and is_incomplete
            and interview.status == InterviewStatus.TECHNICAL
        ):
            interview.status = InterviewStatus.FOLLOW_UP
            next_question = await _pick_next_question(
                interview_id, session, QuestionCategory.TECHNICAL, db, is_follow_up=True
            )
            if next_question:
                session.phase_question_count += 1
            message = "Let me ask a follow-up to explore this further."
        elif session.phase_question_count >= TECHNICAL_QUOTA:
            # Transition to BEHAVIORAL
            interview.status = InterviewStatus.BEHAVIORAL
            session.phase_question_count = 0
            next_question = await _pick_next_question(
                interview_id, session, QuestionCategory.BEHAVIORAL, db
            )
            if next_question:
                session.phase_question_count = 1
            message = "Great, let's move on to some behavioral questions."
        else:
            # Stay in TECHNICAL (or return to TECHNICAL from FOLLOW_UP)
            if interview.status == InterviewStatus.FOLLOW_UP:
                interview.status = InterviewStatus.TECHNICAL
            next_question = await _pick_next_question(
                interview_id, session, QuestionCategory.TECHNICAL, db, force_difficulty=force_diff
            )
            if next_question:
                session.phase_question_count += 1
            message = "Let's step back to fundamentals for a moment." if force_diff == QuestionDifficulty.EASY else "Next question."

    elif interview.status == InterviewStatus.BEHAVIORAL:
        if session.phase_question_count >= BEHAVIORAL_QUOTA:
            # Transition to FINALIZATION
            interview.status = InterviewStatus.FINALIZATION
            session.phase_question_count = 0
            next_question = await _pick_next_question(
                interview_id, session, QuestionCategory.PROJECT, db
            )
            if next_question:
                session.phase_question_count = 1
            message = "We're wrapping up. Let's talk about a specific project from your resume."
        else:
            next_question = await _pick_next_question(
                interview_id, session, QuestionCategory.BEHAVIORAL, db
            )
            if next_question:
                session.phase_question_count += 1
            message = "Next behavioral question."

    # If we ran out of questions, complete the interview
    if next_question is None and interview.status != InterviewStatus.COMPLETED:
        interview.status = InterviewStatus.COMPLETED
        interview.completed_at = datetime.now(timezone.utc)
        interview.skill_scores = session.aggregated_skill_scores
        if session.skill_scores:
            total_score = sum(s for scores in session.skill_scores.values() for s in scores)
            total_count = sum(len(v) for v in session.skill_scores.values())
            interview.overall_score = round(total_score / max(total_count, 1), 1)
        else:
            interview.overall_score = 0.0
            
        message = "Interview completed — all questions have been covered."
        await _add_conversation_message(interview_id, "SYSTEM", message, db)
    if next_question:
        await _add_conversation_message(interview_id, "AI", next_question.question_text, db)

    # Trigger Report Generation if interview was completed during this step
    if interview.status == InterviewStatus.COMPLETED:
        from app.worker import generate_interview_report_task
        generate_interview_report_task.delay(str(interview_id))

    await db.commit()

    next_q_info = _question_to_info(next_question) if next_question else None

    return SubmitAnswerResponse(
        evaluation=AnswerEvaluationResponse(
            technical_correctness=eval_result.technical_correctness,
            relevance=eval_result.relevance,
            depth=eval_result.depth,
            reasoning=eval_result.reasoning,
            clarity=eval_result.clarity,
            completeness=eval_result.completeness,
            overall_score=eval_result.overall_score,
            feedback=eval_result.feedback,
            missing_concepts=eval_result.missing_concepts,
            strengths=eval_result.strengths,
            weaknesses=eval_result.weaknesses,
        ),
        next_question=next_q_info,
        interview_status=interview.status,
        message=message,
    )


async def get_interview_state(interview_id: uuid.UUID, db: AsyncSession) -> InterviewStateResponse:
    """Return the current interview state for the frontend."""
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        raise ValueError("Interview not found")

    session = _get_session(interview_id)

    # Load conversation history
    msg_result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.interview_id == interview_id)
        .order_by(ConversationMessage.timestamp)
    )
    messages = msg_result.scalars().all()
    history = [{"role": m.role.value, "content": m.content} for m in messages]

    # Current question info
    current_q_info: CurrentQuestionInfo | None = None
    if session.current_question_id:
        q_result = await db.execute(
            select(InterviewQuestion).where(InterviewQuestion.id == session.current_question_id)
        )
        q = q_result.scalar_one_or_none()
        if q:
            current_q_info = _question_to_info(q)

    return InterviewStateResponse(
        interview_id=str(interview_id),
        status=interview.status,
        current_question=current_q_info,
        current_difficulty=session.current_difficulty.value,
        questions_asked=len(session.questions_asked),
        total_questions=interview.total_questions,
        skill_scores=session.aggregated_skill_scores,
        overall_score=interview.overall_score,
        conversation_history=history,
    )
