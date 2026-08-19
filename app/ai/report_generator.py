import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.interview import Interview
from app.models.question import InterviewQuestion, QuestionCategory
from app.models.answer import InterviewAnswer
from app.models.evaluation import Evaluation
from app.models.report import InterviewReport

logger = logging.getLogger(__name__)

async def generate_interview_report(interview_id: uuid.UUID, db: AsyncSession) -> InterviewReport:
    """
    Generate the final interview report.
    Fetches all questions, answers, and evaluations for the session.
    Computes averaged scores and uses a mock LLM for qualitative insights.
    Converts the 0-10 scale used during the interview to a 0-100 scale for the report.
    """
    # Fetch evaluations
    query = (
        select(Evaluation, InterviewQuestion, InterviewAnswer)
        .join(InterviewAnswer, Evaluation.answer_id == InterviewAnswer.id)
        .join(InterviewQuestion, InterviewAnswer.question_id == InterviewQuestion.id)
        .where(InterviewQuestion.interview_id == interview_id)
    )
    result = await db.execute(query)
    records = result.all()

    if not records:
        logger.warning(f"No evaluations found for interview {interview_id}")
        # Return a zeroed report if nothing exists
        return InterviewReport(
            interview_id=interview_id,
            overall_score=0.0,
            technical_score=0.0,
            behavioral_score=0.0,
            problem_solving_score=0.0,
            communication_score=0.0,
            summary="No questions answered.",
            strong_skills=[],
            weak_skills=[],
            technical_gaps=[],
            best_answers=[],
            weak_answers=[],
            recommended_topics=[],
            recommendation="Cannot evaluate: insufficient data. Disclaimer: This recommendation is AI-assisted and should not be the sole basis for hiring."
        )

    # Calculate raw averages
    tech_scores = []
    behav_scores = []
    prob_scores = []
    comm_scores = []
    overall_scores = []

    strong_skills_set = set()
    weak_skills_set = set()
    missing_concepts_list = []
    best_answers_list = []
    weak_answers_list = []
    recommended_topics_set = set()

    for eval_obj, q_obj, ans_obj in records:
        overall_scores.append(eval_obj.overall_score)
        
        # Communication is tied to clarity
        comm_scores.append(eval_obj.clarity)
        
        if q_obj.category == QuestionCategory.TECHNICAL:
            tech_scores.append(eval_obj.overall_score)
            prob_scores.append(eval_obj.reasoning)
        elif q_obj.category == QuestionCategory.BEHAVIORAL:
            behav_scores.append(eval_obj.overall_score)
            
        if q_obj.skill_tag:
            if eval_obj.overall_score >= 7.5:
                strong_skills_set.add(q_obj.skill_tag)
            elif eval_obj.overall_score <= 5.0:
                weak_skills_set.add(q_obj.skill_tag)
                recommended_topics_set.add(q_obj.skill_tag)

        if eval_obj.missing_concepts:
            missing_concepts_list.extend(eval_obj.missing_concepts)

        if eval_obj.overall_score >= 8.0:
            if eval_obj.feedback:
                best_answers_list.append(eval_obj.feedback)
            elif q_obj.skill_tag:
                best_answers_list.append(f"Strong response in {q_obj.skill_tag}")
        elif eval_obj.overall_score <= 5.0:
            if eval_obj.feedback:
                weak_answers_list.append(eval_obj.feedback)
            elif q_obj.skill_tag:
                weak_answers_list.append(f"Weak response in {q_obj.skill_tag}")

    # Helper to calculate average and scale to 0-100
    def _avg(scores_list: list[float]) -> float:
        if not scores_list:
            return 0.0
        return round((sum(scores_list) / len(scores_list)) * 10.0, 1)

    overall = _avg(overall_scores)
    tech = _avg(tech_scores)
    behav = _avg(behav_scores)
    prob = _avg(prob_scores)
    comm = _avg(comm_scores)

    # Dedup and limit lists
    technical_gaps = list(set(missing_concepts_list))[:5]
    best_answers = best_answers_list[:3] if best_answers_list else ["No highly rated answers."]
    weak_answers = weak_answers_list[:3] if weak_answers_list else ["No poorly rated answers."]
    recommended_topics = list(recommended_topics_set)[:5]

    # AI Generation for insights
    from openai import AsyncOpenAI
    from app.core.config import settings
    
    api_key = settings.OPENAI_API_KEY
    if api_key and api_key.startswith("gsk_"):
        base_url = "https://api.groq.com/openai/v1"
        model_name = "openai/gpt-oss-120b"
    elif api_key:
        base_url = None
        model_name = "gpt-4o-mini"
    else:
        base_url = settings.OLLAMA_BASE_URL
        model_name = settings.OLLAMA_MODEL

    summary_text = "Interview completed."
    recommendation_text = "No recommendation."
    
    if api_key or base_url:
        try:
            client = AsyncOpenAI(api_key=api_key or "ollama", base_url=base_url)
            prompt = f"""You are an expert technical recruiter and engineering manager evaluating a candidate.
Based on the following data, generate a final JSON report for the candidate.

Overall Score: {overall}/100
Technical Score: {tech}/100
Behavioral Score: {behav}/100
Strong Skills Found: {list(strong_skills_set)}
Weak Skills Found: {list(weak_skills_set)}
Technical Gaps Identified: {technical_gaps}
Best Answers Excerpts: {best_answers}
Weak Answers Excerpts: {weak_answers}

Generate a JSON object with exactly these string keys:
- "summary": A personalized, professional paragraph summarizing their performance.
- "recommendation": A detailed hiring recommendation based on their score (e.g. "Proceed to next stage", "Consider for junior role", "Do not proceed"). Be honest but constructive.
"""
            response = await client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            import json
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            summary_text = data.get("summary", summary_text)
            recommendation_text = data.get("recommendation", recommendation_text) + "\n\nDisclaimer: This recommendation is AI-assisted."
        except Exception as e:
            logger.error(f"Failed to generate report insights with AI: {e}")
            summary_text = f"The candidate completed the interview with an overall score of {overall}/100."
            recommendation_text = "Error generating AI recommendation."

    report = InterviewReport(
        interview_id=interview_id,
        overall_score=overall,
        technical_score=tech,
        behavioral_score=behav,
        problem_solving_score=prob,
        communication_score=comm,
        summary=summary_text,
        strong_skills=list(strong_skills_set),
        weak_skills=list(weak_skills_set),
        technical_gaps=technical_gaps,
        best_answers=best_answers,
        weak_answers=weak_answers,
        recommended_topics=recommended_topics,
        recommendation=recommendation_text
    )

    db.add(report)
    await db.flush()
    return report
