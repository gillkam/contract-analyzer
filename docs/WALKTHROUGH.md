# Walkthrough — How to Run the Contract Analyzer

## Prerequisites

| Requirement | Why |
|-------------|-----|
| **Python 3.10+** | The codebase uses modern typing syntax |
| **Ollama** installed and running | The AI model runs locally via Ollama |
| **deepseek-r1** model pulled | `ollama pull deepseek-r1` — the reasoning model used |
| **~8 GB free RAM** | deepseek-r1 needs memory to load; more = faster |

### Install Ollama (if you haven't)

macOS: `brew install ollama`  or download from <https://ollama.ai>

### Start Ollama and pull the model

```bash
ollama serve              # start the Ollama server (runs on port 11434)
ollama pull deepseek-r1   # download the model (~4.7 GB)
```

---

## 1) Install Python dependencies

From the project root:

```bash
cd contract-analyzer-ollama
pip install -r requirements.txt
```

This installs: FastAPI, Uvicorn, Streamlit, pdfplumber, scikit-learn (TF-IDF),
FAISS, LangChain, orjson, json-repair, tenacity, and others.

---

## 2) Configure `.env`

The project ships with a `.env` file.  The defaults work out of the box:

```dotenv
OLLAMA_MODEL=deepseek-r1
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_TIMEOUT=600
API_BASE=http://127.0.0.1:8000
```

Only change these if your Ollama runs on a different port or you want a
different model.

---

## 3) Start the Backend (FastAPI)

```bash
cd src/backend/analyzer
PYTHONPATH=../  uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

> **Why `PYTHONPATH=../`?**  The `main.py` imports from `chat/rag_chat.py`
> which lives one directory up (`src/backend/chat/`).  This tells Python where
> to find it.

Verify it is running:

```bash
curl http://127.0.0.1:8000/health
# → {"status":"ok","ollama_model":"deepseek-r1"}
```

---

## 4) Start the Frontend (Streamlit)

In a **new terminal**:

```bash
cd src/frontend
streamlit run app.py --server.port 8501
```

Open **http://localhost:8501** in your browser.

---

## 5) Using the App

### Tab 1 — Compliance Analysis

1. Click **Upload PDF** and select a contract (e.g., `samples/Sample Contract.pdf`).
2. Click **Analyze**.
3. Wait ~2–5 minutes (5 sequential LLM calls to deepseek-r1).
4. A color-coded table appears:
   - **Green** = Fully Compliant
   - **Yellow** = Partially Compliant
   - **Red** = Non-Compliant

Each row shows: question, compliance state, confidence %, supporting quotes, and a rationale.

### Tab 2 — Document Chat

1. Upload the same (or different) PDF.
2. Click **Load** to ingest it into the vector store (FAISS).
3. Type any question about the contract in the chat box.
4. The system finds the most relevant paragraphs and generates an answer.

---

## API Endpoints Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Returns model name and status |
| `POST` | `/analyze` | Upload PDF, returns 5 compliance verdicts |
| `POST` | `/rag/ingest` | Upload PDF, embeds into FAISS for chat |
| `POST` | `/rag/chat` | Ask a question, returns AI answer with context |

### Example: Analyze via curl

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F "file=@samples/Sample Contract.pdf" | python -m json.tool
```

### Example: Chat via curl

```bash
# First, ingest
curl -X POST "http://127.0.0.1:8000/rag/ingest?session_id=mytest" \
  -F "file=@samples/Sample Contract.pdf"

# Then, ask
curl -X POST http://127.0.0.1:8000/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "mytest", "question": "What encryption is required?"}'
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: chat` | Set `PYTHONPATH` to include `src/backend/` (see step 3) |
| Port already in use | Kill the process: `lsof -ti :8000 \| xargs kill -9` |
| Timeout on analysis | Increase `OLLAMA_TIMEOUT` in `.env` (default 600 s) |
| Ollama not reachable | Make sure `ollama serve` is running on port 11434 |
| All scores show 50 % | Verify `OLLAMA_MODEL=deepseek-r1` (not a tiny model) |
