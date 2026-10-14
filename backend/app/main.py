import os
from pathlib import Path
from io import BytesIO
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from .schemas import HealthResponse, QuizRequest, QuizResponse
from .quiz_service import QuizGenerationError, generate_quiz

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "8"))
MAX_NOTE_CHARS = int(os.getenv("MAX_NOTE_CHARS", "24000"))

app = FastAPI(title="StudyBuddy AI API", description="Local-first quiz generation using Ollama.", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/")
async def root():
    return {"name": "StudyBuddy AI API", "docs": "/docs", "status": "running"}


@app.get("/api/health", response_model=HealthResponse)
async def health():
    reachable, detail = False, "Ollama is not reachable."
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            response.raise_for_status()
            data = response.json()
            reachable = True
            installed = [item.get("name", "") for item in data.get("models", [])]
            found = any(name == OLLAMA_MODEL or name.startswith(OLLAMA_MODEL + ":") for name in installed)
            detail = "Ollama is ready." if found else f"Ollama is running, but '{OLLAMA_MODEL}' may not be installed. Run `ollama pull {OLLAMA_MODEL}`."
    except Exception:
        pass
    return HealthResponse(status="ok" if reachable else "degraded", ollama_reachable=reachable, model=OLLAMA_MODEL, detail=detail)


@app.post("/api/extract")
async def extract_notes(file: UploadFile = File(...)):
    filename = file.filename or "notes.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".txt", ".md", ".pdf"}:
        raise HTTPException(status_code=400, detail="Supported files: PDF, TXT, and Markdown (.md).")
    raw = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_UPLOAD_MB} MB limit.")
    try:
        if suffix == ".pdf":
            reader = PdfReader(BytesIO(raw))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            text = raw.decode("utf-8-sig")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read the file. Try UTF-8 text or another PDF.") from exc
    text = text.strip()
    if len(text) < 40:
        raise HTTPException(status_code=400, detail="Not enough readable text. Scanned PDFs need OCR; try a text-based PDF.")
    truncated = len(text) > MAX_NOTE_CHARS
    text = text[:MAX_NOTE_CHARS]
    return {"filename": filename, "text": text, "characters": len(text), "truncated": truncated,
            "message": f"Extracted {len(text):,} characters." + (" Notes shortened to fit the configured limit." if truncated else "")}


@app.post("/api/quiz", response_model=QuizResponse)
async def create_quiz(request: QuizRequest):
    try:
        result = await generate_quiz(request.notes[:MAX_NOTE_CHARS], request.question_count, request.difficulty,
                                     request.topic, OLLAMA_BASE_URL, OLLAMA_MODEL)
    except QuizGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return QuizResponse(title=result["title"], questions=result["questions"], model=OLLAMA_MODEL)
