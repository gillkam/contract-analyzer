"""
Unit tests for backend/analyzer/models.py

Covers:
  - Pydantic schema validation for all models
  - Edge cases (missing fields, invalid values)
"""

import pytest


def _import_models():
    from models import (
        ComplianceItem, AnalyzeResponse, ChatRequest, ChatResponse,
        RAGIngestResponse, RAGChatRequest, RAGChatResponse,
    )
    return (
        ComplianceItem, AnalyzeResponse, ChatRequest, ChatResponse,
        RAGIngestResponse, RAGChatRequest, RAGChatResponse,
    )


class TestComplianceItem:
    def test_valid_item(self):
        ComplianceItem = _import_models()[0]
        item = ComplianceItem(
            compliance_question="Password Management",
            compliance_state="Fully Compliant",
            confidence=85,
            relevant_quotes=["Section 3.1"],
            rationale="All requirements met.",
        )
        assert item.compliance_question == "Password Management"
        assert item.compliance_state == "Fully Compliant"
        assert item.confidence == 85

    def test_invalid_state_rejected(self):
        ComplianceItem = _import_models()[0]
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ComplianceItem(
                compliance_question="Test",
                compliance_state="Maybe Compliant",
                confidence=50,
                relevant_quotes=[],
                rationale="test",
            )

    def test_confidence_out_of_range(self):
        ComplianceItem = _import_models()[0]
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ComplianceItem(
                compliance_question="Test",
                compliance_state="Fully Compliant",
                confidence=150,
                relevant_quotes=[],
                rationale="test",
            )

    def test_confidence_none_allowed(self):
        ComplianceItem = _import_models()[0]
        item = ComplianceItem(
            compliance_question="Test",
            compliance_state="Non-Compliant",
            confidence=None,
            relevant_quotes=[],
            rationale="Not found.",
        )
        assert item.confidence is None

    def test_empty_quotes_allowed(self):
        ComplianceItem = _import_models()[0]
        item = ComplianceItem(
            compliance_question="Test",
            compliance_state="Non-Compliant",
            confidence=0,
            relevant_quotes=[],
            rationale="Nothing found.",
        )
        assert item.relevant_quotes == []


class TestAnalyzeResponse:
    def test_valid_response(self):
        ComplianceItem, AnalyzeResponse = _import_models()[:2]
        item = ComplianceItem(
            compliance_question="Test Q",
            compliance_state="Partially Compliant",
            confidence=60,
            relevant_quotes=[],
            rationale="Partial coverage.",
        )
        resp = AnalyzeResponse(session_id="abc-123", items=[item])
        assert resp.session_id == "abc-123"
        assert len(resp.items) == 1


class TestChatModels:
    def test_chat_request(self):
        ChatRequest = _import_models()[2]
        req = ChatRequest(question="What is the password policy?")
        assert req.question == "What is the password policy?"
        assert req.session_id is None

    def test_chat_request_with_session(self):
        ChatRequest = _import_models()[2]
        req = ChatRequest(session_id="s1", question="Tell me more.")
        assert req.session_id == "s1"

    def test_chat_response(self):
        ChatResponse = _import_models()[3]
        resp = ChatResponse(session_id="s1", answer="Here is the answer.")
        assert resp.answer == "Here is the answer."


class TestRAGModels:
    def test_rag_ingest_response(self):
        RAGIngestResponse = _import_models()[4]
        resp = RAGIngestResponse(session_id="r1", chunks_added=42)
        assert resp.chunks_added == 42

    def test_rag_chat_request(self):
        RAGChatRequest = _import_models()[5]
        req = RAGChatRequest(session_id="r1", question="Summarize encryption.")
        assert req.session_id == "r1"

    def test_rag_chat_response(self):
        RAGChatResponse = _import_models()[6]
        resp = RAGChatResponse(session_id="r1", answer="TLS 1.2 is used.", used_context=["chunk1"])
        assert resp.used_context == ["chunk1"]

    def test_rag_chat_response_default_context(self):
        RAGChatResponse = _import_models()[6]
        resp = RAGChatResponse(session_id="r1", answer="Answer")
        assert resp.used_context == []
