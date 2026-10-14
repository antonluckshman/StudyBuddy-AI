# StudyBuddy AI

A local-first AI study companion. Upload PDF/TXT/Markdown lecture notes, generate multiple-choice questions with Ollama, answer them interactively, and review explanations.

## Requirements
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/)

## Run it on Windows (PowerShell)

1. Install Ollama, then download a small model:
   ```powershell
   ollama pull qwen2.5:3b
   ```
   Ollama normally runs as a background service after installation.

2. Start the backend:
   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. In a second terminal, start the frontend:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
   Open http://127.0.0.1:5173

Backend docs: http://127.0.0.1:8000/docs

## macOS/Linux
Use `python3 -m venv .venv`, `source .venv/bin/activate`, then follow the same pip/uvicorn steps. Start the frontend with `npm install && npm run dev`.

## Configuration
Edit `backend/.env`:
- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `OLLAMA_MODEL=qwen2.5:3b`
- `MAX_UPLOAD_MB=8`
- `MAX_NOTE_CHARS=24000`

Use `ollama list` to see installed models. You can change `OLLAMA_MODEL` to another model available in Ollama.

## Privacy and limitations
Notes are sent only to the Ollama server configured in `OLLAMA_BASE_URL`; keep it pointed at your own computer for local processing. Uploaded files and quizzes are not saved to a database. Do not upload sensitive content if Ollama is configured to use a remote machine. AI-generated answers can be wrong, so verify important details against the source notes. Scanned PDFs are not OCR'd in this MVP.
