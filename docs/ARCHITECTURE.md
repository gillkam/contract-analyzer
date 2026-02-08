
# Architecture — Contract Compliance Analyzer

## What This Project Does (Plain English)

You upload a PDF contract. The system reads it, finds the relevant sections for
five security-compliance questions, sends each question to a local AI model
(deepseek-r1 running on Ollama), and gets back a structured verdict:
**Fully / Partially / Non-Compliant** with a confidence score, supporting quotes,
and a one-sentence rationale.  There is also a "Document Chat" tab where you can
ask free-form questions about the contract.

---

## High-Level Components

```
┌──────────────┐        HTTP        ┌────────────────────┐       HTTP        ┌───────────┐
│   Streamlit  │  ───────────────►  │   FastAPI Backend   │  ─────────────►  │  Ollama   │
│   Frontend   │  ◄───────────────  │   (port 8000)       │  ◄─────────────  │  (11434)  │
│  (port 8501) │     JSON resp      │                     │    LLM reply     │ deepseek  │
└──────────────┘                    └────────────────────┘                   └───────────┘
      ▲                                  │          │
      │  user uploads PDF                │          │
      │  sees results table              │          │
      │  chats with document             │          │
                                    Analyzer    RAG Chat
                                   (TF-IDF)    (FAISS)
```

| Layer | Tech | Role |
|-------|------|------|
| **Frontend** | Streamlit (`src/frontend/app.py`) | Upload PDF, display compliance table, document chat UI |
| **API Server** | FastAPI + Uvicorn (`src/backend/analyzer/main.py`) | REST endpoints: `/analyze`, `/rag/ingest`, `/rag/chat`, `/health` |
| **Compliance Analyzer** | `analyzer.py`, `prompts.py` | Extracts PDF → retrieves relevant chunks → calls LLM per question → parses JSON → enforces thresholds |
| **RAG Chat** | `chat/rag_chat.py` | Embeds PDF chunks into FAISS vector store, answers free-form questions via similarity search + LLM |
| **PDF Extraction** | pdfplumber (`utils_pdf.py`) | Extracts page text **and** table rows from the PDF |
| **LLM Client** | `ollama_client.py` | Thin wrapper around Ollama's `/api/chat` HTTP endpoint |
| **LLM** | Ollama + deepseek-r1 | Local inference — no data leaves your machine |

---

## Detailed Data Flow — Compliance Analysis

Here is exactly what happens when you click **Analyze**:

### Step 1 — PDF Upload
```
Browser → POST /analyze (multipart PDF) → FastAPI
```

### Step 2 — Text Extraction (`utils_pdf.py`)
pdfplumber opens the PDF and creates two kinds of Documents per page:
- **Page text** — the full text of that page.
- **Table rows** — cells joined by `|`, rows joined by `;`.

This ensures we capture both running prose (contract body) **and** structured
tables (Exhibit G control matrices).

### Step 3 — Context Retrieval (`analyzer.py → _pick_context_chunks`)
For each of the 5 compliance questions:
1. The full document set is **split** into ~1500-character chunks with 200-char
   overlap (`RecursiveCharacterTextSplitter`).
2. A **TF-IDF retriever** ranks those chunks against the question's keyword list
   (defined in `prompts.py → QUESTION_KEYWORDS`).
3. The **top-10 text chunks** and **top-6 table chunks** are returned and
   de-duplicated.

*Why TF-IDF and not embeddings?*  TF-IDF is instant (no GPU, no model load),
 perfectly reproducible, and works well when you already know the exact
 keywords to search for.  Embeddings are used separately in the RAG Chat
 feature where questions are unpredictable.

### Step 4 — LLM Call (`ollama_client.py`)
The selected chunks are injected into a structured prompt:

```
SYSTEM: "You are a strict contract compliance auditor. For each numbered
         sub-requirement, check if the contract has EXPLICIT evidence…
         Return ONLY a JSON object with: compliance_state, confidence,
         relevant_quotes, rationale."

USER:   "CONTEXT:\n{retrieved chunks}\n\nREQUIREMENT:\n{sub-requirements}"
```

This is sent to `deepseek-r1` via Ollama with **deterministic settings**:
`temperature=0.0, top_p=1.0, seed=42`.

### Step 5 — Response Parsing (`analyzer.py → _parse_llm_json`)
deepseek-r1 wraps its reasoning inside `<think>…</think>` tags before
producing the answer.  The parser:
1. **Strips** `<think>…</think>` blocks and code fences.
2. **Extracts** the first `{…}` JSON object via regex.
3. **Repairs** malformed JSON (`json_repair` library).
4. **Parses** with `orjson` (fast binary JSON parser).
5. **Retries** up to 3 times on failure (tenacity).

### Step 6 — Threshold Enforcement (`_apply_policy`)
The LLM's confidence is clamped to 0–98 and mapped to a state:

| Confidence | State |
|------------|-------|
| < 40 | Non-Compliant |
| 40 – 84 | Partially Compliant |
| ≥ 85 | Fully Compliant |

This makes scoring **deterministic** — the same confidence always maps to the
same state, even if the LLM's text label disagrees.

### Step 7 — Validation & Response
Each result is validated by a Pydantic model (`ComplianceResult`), then
returned as JSON to the frontend, which renders a color-coded table.

---

## Detailed Data Flow — Document Chat (RAG)

1. **Ingest**: User uploads PDF → `POST /rag/ingest` → PyPDF2 extracts text →
   `RecursiveCharacterTextSplitter` (1000 chars / 150 overlap) → embedded
   with `OllamaEmbeddings` → stored in an **in-memory FAISS** vector store.
2. **Chat**: User asks a question → `POST /rag/chat` → FAISS similarity search
   retrieves the top-4 most relevant chunks → chunks + question sent to
   `deepseek-r1` → answer returned (with `<think>` tags stripped).

---

## Prompt Design Philosophy

### Why one LLM call per question (not one call for all 5)?
- Each question gets its **own dedicated context** (only relevant chunks).
- The prompt stays short and focused — better accuracy.
- If one question fails/retries, the others are unaffected.

### Why numbered sub-requirements?
Each compliance question is decomposed into 4–7 numbered checklist items
(see `prompts.py → COMPLIANCE_REQUIREMENTS`).  The LLM is told:

> "Mark YES only if there is explicit evidence.  confidence = (YES count / total) × 100."

This converts a subjective "how compliant is this?" into an objective counting
exercise.  The LLM just needs to decide YES/NO per item, then do arithmetic.

### Why no `format: "json"` in the Ollama call?
deepseek-r1 uses a `<think>` reasoning chain internally.  Setting
`format: "json"` suppresses that chain, causing the model to skip reasoning
and guess — which produces inaccurate, uniform scores.  Instead, we let it
think freely and extract the JSON after the fact.

### Why `seed: 42` + `temperature: 0`?
To make results **deterministic**.  Running the same contract twice produces
the same scores.  This is critical for audit-grade tools.

---

## Key Tradeoffs

| Decision | Benefit | Cost |
|----------|---------|------|
| **TF-IDF retrieval** (compliance) | Instant, reproducible, no GPU needed | Can miss content if keywords don't match garbled PDF text |
| **FAISS embeddings** (RAG chat) | Handles unpredictable questions via semantic similarity | Slower initial indexing; requires embedding model |
| **Local Ollama** (no cloud API) | Privacy — zero data leaves your machine | Slower inference; depends on local GPU/CPU power |
| **One LLM call per question** | Focused context, independent retries | 5× the latency vs. a single "answer all" call |
| **No `format: "json"`** | deepseek-r1 reasons properly | Must strip `<think>` tags; parse JSON from free-text |
| **Deterministic seeds** | Reproducible audits | Slightly less creative/flexible responses |
| **In-memory FAISS** | No database to install | State lost on server restart |
| **pdfplumber for extraction** | Handles tables well | Slower than PyPDF2 for text-only pages |

---

## Project Structure

```
contract-analyzer-ollama/
├── .env                          # All configuration (model, URLs, timeouts, tuning)
├── requirements.txt              # Python dependencies
├── samples/                      # Sample PDF contracts for testing
├── docs/
│   ├── ARCHITECTURE.md           # ← you are here
│   ├── WALKTHROUGH.md            # How to run the project
│   └── ASSIGNMENT.md             # Original assignment brief
└── src/
    ├── backend/
    │   ├── analyzer/             # Compliance analysis engine
    │   │   ├── main.py           # FastAPI app + all endpoints
    │   │   ├── analyzer.py       # Core: PDF → chunks → LLM → parse → score
    │   │   ├── prompts.py        # 5 questions, requirements, keywords, prompt templates
    │   │   ├── ollama_client.py  # HTTP client for Ollama API
    │   │   ├── utils_pdf.py      # PDF extraction (pdfplumber)
    │   │   └── models.py         # Pydantic request/response schemas
    │   └── chat/
    │       └── rag_chat.py       # RAG Chat: FAISS + Ollama for Q&A
    ├── frontend/
    │   └── app.py                # Streamlit UI (compliance + chat tabs)
    └── tests/                    # Test files
```

---

## Configuration (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_MODEL` | `deepseek-r1` | Which Ollama model to use |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server address |
| `OLLAMA_TIMEOUT` | `600` | Max seconds to wait for LLM response |
| `CORS_ORIGINS` | `*` | Allowed frontend origins |
| `RAG_CHUNK_SIZE` | `1000` | Chunk size for RAG document splitting |
| `RAG_CHUNK_OVERLAP` | `150` | Overlap between RAG chunks |
| `RAG_SIMILARITY_K` | `4` | Number of chunks retrieved per chat question |
| `ANALYZE_TIMEOUT` | `300` | Frontend timeout for `/analyze` calls |
| `CHAT_TIMEOUT` | `120` | Frontend timeout for chat calls |
