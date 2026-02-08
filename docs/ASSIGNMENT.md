# Assignment Brief

## Goal

Build an application that:

1. Accepts a **PDF contract** as input.
2. **Parses** the document (extracts text and tables).
3. **Evaluates** the contract against **five predefined security-compliance questions** using a Generative AI model.
4. Returns **structured results** in a web UI.

## The Five Compliance Questions

| # | Question |
|---|----------|
| 1 | Does the contract require data encryption at rest **and** in transit? |
| 2 | Are there clauses for regular security audits and vulnerability assessments? |
| 3 | Does the contract define incident response and breach notification procedures? |
| 4 | Are access control and identity-management requirements specified? |
| 5 | Does the contract address data retention, disposal, and backup recovery? |

Each question must be answered with one of three states:

- **Fully Compliant** — all sub-requirements are clearly covered.
- **Partially Compliant** — some but not all sub-requirements are present.
- **Non-Compliant** — the topic is not meaningfully addressed.

## Deliverables

| Deliverable | How This Project Satisfies It |
|-------------|-------------------------------|
| PDF upload | Streamlit "Upload PDF" button, FastAPI `/analyze` endpoint |
| Text extraction | `utils_pdf.py` using pdfplumber (text + tables) |
| AI analysis | 5 individual LLM calls to deepseek-r1 via Ollama |
| Structured output | JSON with `state`, `confidence`, `quotes`, `rationale` per question |
| Web UI | Streamlit app with color-coded compliance table |
| Document chat (bonus) | RAG pipeline: FAISS vector store + `/rag/chat` endpoint |

## Constraints

- The AI model runs **locally** via Ollama — no data is sent to external APIs.
- Deterministic settings are used (temperature 0, seed 42) for reproducible results.
- The five questions and allowed compliance states are fixed by the assignment spec.
