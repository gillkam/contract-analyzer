from pydantic import BaseModel, Field
from typing import Literal


class ComplianceItem(BaseModel):
    compliance_question: str
    compliance_state: Literal["Fully Compliant", "Partially Compliant", "Non-Compliant"]
    confidence: int | None = Field(None, ge=0, le=100)
    relevant_quotes: list[str] = []
    rationale: str


class AnalyzeResponse(BaseModel):
    session_id: str
    items: list[ComplianceItem]


class ChatRequest(BaseModel):
    session_id: str | None = None
    question: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str


class RAGIngestResponse(BaseModel):
    session_id: str
    chunks_added: int


class RAGChatRequest(BaseModel):
    session_id: str
    question: str


class RAGChatResponse(BaseModel):
    session_id: str
    answer: str
    used_context: list[str] = []