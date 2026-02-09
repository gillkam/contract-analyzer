
import uuid
import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from models import (
    AnalyzeResponse, ComplianceItem, ChatRequest, ChatResponse,
    RAGIngestResponse, RAGChatRequest, RAGChatResponse
)
from analyzer import analyze_pdf_bytes
from chat.rag_chat import get_rag_state

load_dotenv()

# ── configurable via .env ──
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
CORS_ORIGINS = os.getenv("CORS_ORIGINS").split(",")

app = FastAPI(title="Contract Compliance Analyzer (Ollama)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "ollama_model": OLLAMA_MODEL}

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...), session_id: str | None = None):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF.")

    sid = session_id or str(uuid.uuid4())
    pdf_bytes = await file.read()

    items_json = analyze_pdf_bytes(pdf_bytes, model=OLLAMA_MODEL)
    items: list[ComplianceItem] = []
    for it in items_json:
        try:
            items.append(ComplianceItem(**it))
        except ValidationError as ve:
            items.append(ComplianceItem(
                compliance_question=it.get("compliance_question", "Unknown"),
                compliance_state="Non-Compliant",
                confidence=0,
                relevant_quotes=[],
                rationale=f"Invalid item schema: {ve}"
            ))
    return AnalyzeResponse(session_id=sid, items=items)

# ============== RAG Chat Endpoints ==============

@app.post("/rag/ingest", response_model=RAGIngestResponse)
async def rag_ingest(file: UploadFile = File(...), session_id: str | None = None):
    """Ingest a PDF into the RAG vector store."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF.")
    
    sid = session_id or str(uuid.uuid4())
    pdf_bytes = await file.read()
    
    rag = get_rag_state(sid)
    chunks_added = rag.load_pdf(pdf_bytes)
    
    return RAGIngestResponse(session_id=sid, chunks_added=chunks_added)


@app.post("/rag/chat", response_model=RAGChatResponse)
async def rag_chat(req: RAGChatRequest):
    """Chat with the ingested document using RAG."""
    rag = get_rag_state(req.session_id)
    
    if rag.count() == 0:
        raise HTTPException(status_code=400, detail="No documents ingested yet. Please upload a PDF first.")
    
    result = rag.chat(req.question)
    
    return RAGChatResponse(
        session_id=req.session_id,
        answer=result["answer"],
        used_context=result["context"][:3]
    )
