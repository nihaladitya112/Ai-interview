# AI Interviewer Platform 🤖👔

An intelligent, full-stack AI interview platform that evaluates candidates' resumes, generates tailored interview questions, and conducts interviews using Local AI models (Ollama) and lightning-fast audio transcription (Groq/OpenAI).

## 🌟 Features
* **AI Resume Parsing**: Extracts skills and experience automatically from uploaded resumes (PDF/DOCX/TXT).
* **Smart Matching**: Uses `pgvector` to compare candidate embeddings with job requirements to determine the best fit.
* **Dynamic AI Interviews**: Uses **Ollama (Llama 3.2)** to generate context-aware interview questions based on the candidate's actual skills.
* **Voice-to-Text**: Built-in support for Whisper transcription (via Groq/OpenAI) for audio responses.
* **Beautiful Dashboard**: Custom-built, responsive UI using TailwindCSS-inspired design tokens.
* **Asynchronous Backend**: Powered by FastAPI, Celery, and Redis for heavy AI workloads.

---

## 🏗️ Architecture Stack
* **Backend:** Python 3.12+, FastAPI, SQLAlchemy (Async), Pydantic
* **Database:** PostgreSQL (with `pgvector` extension)
* **Background Workers:** Celery + Redis
* **AI Models:** Ollama (Local LLM), Whisper (Audio Transcription)
* **Frontend:** Vanilla HTML/JS + CSS

---

## 🚀 Quickstart Guide

### 1. Prerequisites
You must have the following installed on your machine:
* **Docker** & Docker Compose (for the database and Redis)
* **Python 3.10+**
* **Ollama** installed locally (with the `llama3.2:1b` model pulled).
  ```bash
  ollama run llama3.2:1b
  ```

### 2. Environment Setup
Clone the repository and set up your virtual environment:
```bash
git clone https://github.com/yourusername/ai-interview.git
cd ai-interview
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create your environment variables by copying the example file:
```bash
cp .env.example .env
```
*Note: If you plan to use audio transcription, be sure to add your Groq API key (`gsk_...`) to the `OPENAI_API_KEY` field in the `.env` file.*

### 3. Start the Infrastructure (Database & Redis)
Start the PostgreSQL (pgvector) database and Redis instance using Docker:
```bash
docker compose up db redis -d
```
*(Wait a few seconds for the database to fully initialize).*

### 4. Run the Servers
You will need to run the **Backend API** and the **Celery Worker** in two separate terminal windows.

**Terminal 1 - FastAPI Server:**
```bash
source venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

**Terminal 2 - Celery Worker:**
```bash
source venv/bin/activate
celery -A app.worker.celery_app worker --loglevel=info
```

### 5. Access the Platform
Open your browser and navigate to:
**[http://localhost:8001](http://localhost:8001)**

You can register a new candidate account, upload a resume, and begin your first AI interview!

---

## 🧪 Testing
To run the automated test suite:
```bash
pytest tests/
```

## 📄 License
MIT License
