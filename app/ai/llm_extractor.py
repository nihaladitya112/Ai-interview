import json
import logging
import re
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Robust keyword-based fallback parser (no LLM needed)
# ─────────────────────────────────────────────────────────────────────────────

# Comprehensive list of known technologies/skills to scan for
_KNOWN_SKILLS = [
    # Languages
    "Java", "Python", "JavaScript", "TypeScript", "C", "C++", "C#", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "Dart", "Perl", "Lua",
    "MATLAB", "Shell", "Bash", "PowerShell", "Objective-C", "Haskell", "Elixir",
    # Frontend
    "HTML", "CSS", "React", "React.js", "Angular", "Vue", "Vue.js", "Svelte",
    "Next.js", "Nuxt.js", "jQuery", "Bootstrap", "Tailwind", "TailwindCSS",
    "SASS", "SCSS", "Material UI", "Chakra UI",
    # Backend
    "Node.js", "Express", "Express.js", "Django", "Flask", "FastAPI",
    "Spring", "Spring Boot", ".NET", "ASP.NET", "Rails", "Ruby on Rails",
    "Laravel", "NestJS", "Gin", "Fiber",
    # Databases
    "MongoDB", "MySQL", "PostgreSQL", "SQL", "SQLite", "Redis", "Cassandra",
    "DynamoDB", "Firebase", "Firestore", "MariaDB", "Oracle", "Neo4j",
    "Elasticsearch", "Supabase",
    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes", "Jenkins",
    "CI/CD", "Terraform", "Ansible", "Nginx", "Apache", "Heroku", "Vercel",
    "Netlify", "DigitalOcean", "Linux", "Git", "GitHub", "GitLab",
    # Data / ML / AI
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Keras",
    "Scikit-learn", "Pandas", "NumPy", "Matplotlib", "Seaborn", "OpenCV",
    "NLTK", "spaCy", "Hugging Face", "LangChain",
    "Data Structures", "Algorithms", "Data Structures & Algorithms",
    "Generative AI", "LLM", "RAG", "Retrieval-Augmented Generation",
    "Natural Language Processing", "NLP", "Computer Vision",
    # Mobile
    "Android", "iOS", "React Native", "Flutter", "Xamarin", "Ionic",
    # Other
    "REST", "RESTful", "GraphQL", "gRPC", "WebSocket", "Microservices",
    "Agile", "Scrum", "JIRA", "Figma", "Postman", "Swagger",
    "Object-Oriented Programming", "OOP", "Functional Programming",
]


def _extract_name(text: str) -> str:
    """Extract the candidate's name from the first few lines."""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if lines:
        # The first non-empty line is usually the name
        first_line = lines[0]
        # Basic validation: a name is typically 2-4 words, no special chars
        if 1 < len(first_line.split()) <= 5 and not any(c in first_line for c in ['@', ':', '|', '/']):
            return first_line
    return "Candidate"


def _extract_skills_from_text(text: str) -> tuple[list[str], list[str]]:
    """Scan raw text for known skills and technologies."""
    skills = []
    technologies = []
    text_lower = text.lower()

    tech_categories = {
        "MongoDB", "MySQL", "PostgreSQL", "SQL", "SQLite", "Redis", "Cassandra",
        "DynamoDB", "Firebase", "Firestore", "Docker", "Kubernetes", "Jenkins",
        "Terraform", "Ansible", "Nginx", "AWS", "Azure", "GCP", "Google Cloud",
        "Heroku", "Vercel", "Netlify", "Git", "GitHub", "GitLab", "Linux",
        "Postman", "Swagger", "JIRA", "Figma", "Supabase",
    }

    for skill in _KNOWN_SKILLS:
        # Use word boundary matching to avoid partial matches
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            if skill in tech_categories:
                if skill not in technologies:
                    technologies.append(skill)
            else:
                if skill not in skills:
                    skills.append(skill)

    return skills, technologies


def _extract_projects(text: str) -> list[str]:
    """Extract project names from the resume text."""
    projects = []
    lines = text.split("\n")

    in_projects_section = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        lower = stripped.lower()

        # Detect the "Projects" section header
        if lower in ["projects", "project", "projects:", "personal projects", "academic projects"]:
            in_projects_section = True
            continue

        # End of projects section when we hit another section header
        if in_projects_section and lower in [
            "experience", "work experience", "education", "skills", "technical skills",
            "certifications", "achievements", "awards", "interests", "hobbies",
            "summary", "objective", "references", "publications", "contact",
        ]:
            in_projects_section = False
            continue

        if in_projects_section and stripped:
            # Project names are typically short lines (titles) before descriptions
            # A project title is usually < 60 chars and doesn't start with common description patterns
            if (
                len(stripped) < 80
                and not stripped.startswith(("•", "-", "*", "–", "·"))
                and not stripped[0].islower()
                and not any(stripped.lower().startswith(w) for w in [
                    "developed", "built", "created", "designed", "implemented",
                    "used", "utilized", "worked", "responsible", "focused",
                    "a web", "an app", "the project",
                ])
            ):
                projects.append(stripped)

    return projects


def _extract_education(text: str) -> list[str]:
    """Extract education entries."""
    education = []
    lines = text.split("\n")

    in_education = False
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if lower in ["education", "education:", "academic background"]:
            in_education = True
            continue

        if in_education and lower in [
            "projects", "experience", "skills", "technical skills",
            "certifications", "achievements", "summary",
        ]:
            in_education = False
            continue

        if in_education and stripped and not stripped.replace(".", "").replace(",", "").isdigit():
            # Grab lines that look like degree/institution entries
            if any(kw in lower for kw in [
                "b.tech", "b.sc", "b.s.", "m.tech", "m.sc", "m.s.", "bachelor",
                "master", "phd", "diploma", "intermediate", "class x", "school",
                "university", "institute", "college", "cgpa", "percentage",
            ]):
                education.append(stripped)

    return education


def _fallback_parse(raw_text: str) -> dict:
    """Parse resume using keyword matching when LLM is unavailable."""
    name = _extract_name(raw_text)
    skills, technologies = _extract_skills_from_text(raw_text)
    projects = _extract_projects(raw_text)
    education = _extract_education(raw_text)

    logger.info(f"Fallback parser found: name={name}, skills={skills}, "
                f"technologies={technologies}, projects={projects}")

    return {
        "Name": name,
        "Skills": skills,
        "Technologies": technologies,
        "Projects": projects,
        "Education": education,
        "Experience": [],
        "Certifications": [],
        "Achievements": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main extraction function
# ─────────────────────────────────────────────────────────────────────────────

async def extract_candidate_profile(raw_text: str) -> dict:
    """
    Extracts structured resume data from raw text.
    Tries LLM first, falls back to keyword-based parsing.
    """
    api_key = settings.OPENAI_API_KEY or "ollama"

    if api_key.startswith("gsk_"):
        base_url = "https://api.groq.com/openai/v1"
        model_name = "llama-3.1-70b-versatile"
    elif settings.OPENAI_API_KEY:
        base_url = None
        model_name = "gpt-4o-mini"
    else:
        base_url = settings.OLLAMA_BASE_URL
        model_name = settings.OLLAMA_MODEL

    if not settings.OPENAI_API_KEY and not settings.OLLAMA_BASE_URL:
        return _fallback_parse(raw_text)

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        system_prompt = """You are an expert Resume Parser. 
Extract the candidate's profile from the following resume text.
Return the result strictly as a JSON object with the following keys:
- "Name" (string, the candidate's full name)
- "Skills" (list of strings: programming languages, frameworks, etc.)
- "Technologies" (list of strings: tools, databases, infrastructure, etc.)
- "Projects" (list of strings: titles of projects ONLY, NOT descriptions)
- "Education" (list of strings)
- "Experience" (list of strings: concise job titles and companies)
- "Certifications" (list of strings)
- "Achievements" (list of strings)

Only include technologies and skills that are EXPLICITLY mentioned in the resume. Do not hallucinate or guess.
Ensure valid JSON output. Do not include Markdown backticks in the response.
"""

        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Resume Text:\n{raw_text[:4000]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        content = response.choices[0].message.content.strip()

        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()

        data = json.loads(content)
        logger.info(f"LLM parsed resume: skills={data.get('Skills')}, projects={data.get('Projects')}")
        return data

    except Exception as e:
        logger.error(f"LLM extraction failed: {e}. Using keyword-based fallback.")
        return _fallback_parse(raw_text)


def extract_job_description(raw_text: str) -> dict:
    """
    Mock implementation of LLM job description extraction.
    Returns neutral values so it does not inject technologies
    that are not on the candidate's resume.
    """
    return {
        "Role": "Software Developer",
        "Required skills": [],
        "Preferred skills": [],
        "Technologies": [],
        "Responsibilities": [],
        "Experience": "",
        "Education": "",
        "Seniority": "Mid-Level"
    }

