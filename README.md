# Contract Compliance Analyzer (Ollama)

An offline, privacy-first tool that evaluates PDF contracts against five security-compliance questions using a local LLM (deepseek-r1 via Ollama). Upload a contract, get a per-question compliance verdict with confidence scores, supporting quotes, and rationale — all without sending data to external APIs.

## Features

- **Compliance Analysis** — Assesses contracts against 5 predefined security compliance questions (data encryption, access control, incident response, security training, and data retention).
- **RAG Document Chat** — Ask follow-up questions about an uploaded contract using FAISS-backed retrieval-augmented generation.
- **Deterministic Scoring** — Fixed seed, temperature 0, and threshold-based policy mapping ensure reproducible results across runs.
- **Robust JSON Parsing** — Strips `<think>` tags (deepseek-r1), repairs malformed JSON, and retries up to 3 times.
- **Fully Configurable** — Every tuning knob (chunk size, top-k, LLM params, timeouts) lives in a single `.env` file.

## Architecture

```
PDF Upload
    │
    ▼
pdfplumber ──► page text + table rows
    │
    ▼
TF-IDF Retrieval ──► top-k relevant chunks per question
    │
    ▼
Ollama (deepseek-r1) ──► JSON verdict per question
    │
    ▼
Policy Thresholds ──► deterministic compliance state
    │
    ▼
Streamlit UI ──► results display
```

## Project Structure

```
contract-analyzer-ollama/
├── .env                        # All configuration (required)
├── .env.example                # Template for new setups
├── requirements.txt            # Python dependencies
├── samples/
│   └── Sample Contract.pdf     # Test contract
├── src/
│   ├── backend/
│   │   ├── analyzer/
│   │   │   ├── main.py         # FastAPI app (/health, /analyze, /chat, /rag/*)
│   │   │   ├── analyzer.py     # Core compliance analysis pipeline
│   │   │   ├── ollama_client.py# HTTP wrapper for Ollama API
│   │   │   ├── prompts.py      # 5 compliance questions, keywords, prompt templates
│   │   │   ├── models.py       # Pydantic request/response schemas
│   │   │   └── utils_pdf.py    # PDF extraction (pdfplumber)
│   │   └── chat/
│   │       └── rag_chat.py     # FAISS + OllamaEmbeddings RAG chat
│   └── frontend/
│       └── app.py              # Streamlit UI (2 tabs: Analysis + Chat)
└── docs/
    ├── ARCHITECTURE.md         # Detailed architecture & design decisions
    ├── WALKTHROUGH.md          # Step-by-step run guide & API reference
    └── ASSIGNMENT.md           # Original assignment brief
```

## Prerequisites

- **Python 3.11+**
- **Ollama** installed and running — [https://ollama.com](https://ollama.com)
- **deepseek-r1** model pulled:
  ```bash
  ollama serve          # start Ollama (if not already running)
  ollama pull deepseek-r1
  ```

## Quickstart

### 1. Clone & install dependencies

```bash
cd contract-analyzer-ollama
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work out of the box)
```

### 3. Start the backend

```bash
cd src/backend/analyzer
PYTHONPATH=../ uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Start the frontend (new terminal)

```bash
cd src/frontend
streamlit run app.py --server.port 8501
```

### 5. Use it

Open [http://localhost:8501](http://localhost:8501), upload a PDF contract, and click **Analyze**.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (returns model name) |
| `POST` | `/analyze` | Upload PDF, get 5 compliance verdicts |
| `POST` | `/chat` | Simple chat with Ollama |
| `POST` | `/rag/ingest` | Ingest PDF into FAISS vector store |
| `POST` | `/rag/chat` | RAG-powered Q&A over ingested document |

## Environment Variables

All configuration is centralized in `.env` — the app will **fail fast** if any variable is missing (no hidden defaults).

| Variable | Purpose | Default in `.env.example` |
|----------|---------|--------------------------|
| `OLLAMA_MODEL` | LLM model name | `deepseek-r1` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://127.0.0.1:11434` |
| `OLLAMA_TIMEOUT` | Request timeout (seconds) | `600` |
| `OLLAMA_TEMPERATURE` | LLM temperature | `0.0` |
| `OLLAMA_TOP_P` | Nucleus sampling | `1.0` |
| `OLLAMA_NUM_PREDICT` | Max tokens | `4096` |
| `OLLAMA_SEED` | Reproducibility seed | `42` |
| `CHUNK_SIZE` | Text chunk size (chars) | `1500` |
| `CHUNK_OVERLAP` | Chunk overlap (chars) | `200` |
| `TOP_K_TEXT` | Top-k text chunks per question | `10` |
| `TOP_K_TABLE` | Top-k table chunks per question | `6` |
| `RAG_CHUNK_SIZE` | RAG chat chunk size | `1000` |
| `RAG_CHUNK_OVERLAP` | RAG chat chunk overlap | `150` |
| `RAG_SIMILARITY_K` | RAG similarity results | `4` |
| `API_BASE` | Backend URL (for frontend) | `http://127.0.0.1:8000` |
| `ANALYZE_TIMEOUT` | Frontend analysis timeout (sec) | `300` |
| `CHAT_TIMEOUT` | Frontend chat timeout (sec) | `120` |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Ollama + deepseek-r1 |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| PDF Parsing | pdfplumber |
| Retrieval (Analysis) | TF-IDF (scikit-learn + LangChain) |
| Retrieval (Chat) | FAISS + OllamaEmbeddings |
| JSON Handling | orjson + json-repair + tenacity |
| Config | python-dotenv (.env) |
