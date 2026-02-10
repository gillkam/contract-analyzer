"""
Integration tests for the FastAPI application.

Tests the API endpoints using TestClient (no real Ollama needed).

Covers:
  - GET  /health
  - POST /analyze  (mocked LLM)
  - POST /chat
  - POST /rag/ingest  (mocked RAG)
  - POST /rag/chat     (mocked RAG)
  - Error cases (non-PDF upload, missing session)
"""

import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


def _get_test_client():
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


# ═══════════════════════════════════════════
#  GET /health
# ═══════════════════════════════════════════
class TestHealthEndpoint:
    def test_health_returns_ok(self):
        client = _get_test_client()
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["ollama_model"] == "deepseek-r1"


# ═══════════════════════════════════════════
#  POST /analyze
# ═══════════════════════════════════════════
class TestAnalyzeEndpoint:
    def test_non_pdf_rejected(self):
        client = _get_test_client()
        r = client.post(
            "/analyze",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400
        assert "PDF" in r.json()["detail"]

    @patch("main.analyze_pdf_bytes")
    def test_analyze_success(self, mock_analyze):
        mock_analyze.return_value = [
            {
                "compliance_question": "Password Management",
                "compliance_state": "Partially Compliant",
                "confidence": 57,
                "relevant_quotes": ["Section 3.1"],
                "rationale": "The contract partially covers password management requirements.",
            },
            {
                "compliance_question": "IT Asset Management",
                "compliance_state": "Non-Compliant",
                "confidence": 0,
                "relevant_quotes": [],
                "rationale": "No relevant evidence found in extracted context.",
            },
            {
                "compliance_question": "Security Training & Background Checks",
                "compliance_state": "Fully Compliant",
                "confidence": 92,
                "relevant_quotes": ["Section 5.2"],
                "rationale": "All security training and background check requirements are met.",
            },
            {
                "compliance_question": "Data in Transit Encryption",
                "compliance_state": "Partially Compliant",
                "confidence": 75,
                "relevant_quotes": ["Section 4.2"],
                "rationale": "TLS encryption is specified but certificate management is missing.",
            },
            {
                "compliance_question": "Network Authentication & Authorization Protocols",
                "compliance_state": "Partially Compliant",
                "confidence": 50,
                "relevant_quotes": [],
                "rationale": "Authentication mechanisms mentioned but MFA and RBAC are absent.",
            },
        ]

        client = _get_test_client()
        r = client.post(
            "/analyze",
            files={"file": ("contract.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert r.status_code == 200
        data = r.json()
        assert "session_id" in data
        assert len(data["items"]) == 5
        assert data["items"][0]["compliance_question"] == "Password Management"

    @patch("main.analyze_pdf_bytes")
    def test_analyze_with_session_id(self, mock_analyze):
        mock_analyze.return_value = [
            {
                "compliance_question": q,
                "compliance_state": "Non-Compliant",
                "confidence": 0,
                "relevant_quotes": [],
                "rationale": "No relevant evidence found in the extracted context.",
            }
            for q in [
                "Password Management", "IT Asset Management",
                "Security Training & Background Checks",
                "Data in Transit Encryption",
                "Network Authentication & Authorization Protocols",
            ]
        ]

        client = _get_test_client()
        r = client.post(
            "/analyze?session_id=my-custom-session",
            files={"file": ("contract.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert r.status_code == 200
        assert r.json()["session_id"] == "my-custom-session"


# ═══════════════════════════════════════════
#  POST /rag/ingest
# ═══════════════════════════════════════════
class TestRAGIngestEndpoint:
    def test_non_pdf_rejected(self):
        client = _get_test_client()
        r = client.post(
            "/rag/ingest",
            files={"file": ("test.docx", b"not a pdf", "application/octet-stream")},
        )
        assert r.status_code == 400
        assert "PDF" in r.json()["detail"]

    @patch("main.get_rag_state")
    def test_ingest_success(self, mock_rag):
        mock_state = MagicMock()
        mock_state.load_pdf.return_value = 15
        mock_rag.return_value = mock_state

        client = _get_test_client()
        r = client.post(
            "/rag/ingest",
            files={"file": ("contract.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["chunks_added"] == 15
        assert "session_id" in data


# ═══════════════════════════════════════════
#  POST /rag/chat
# ═══════════════════════════════════════════
class TestRAGChatEndpoint:
    @patch("main.get_rag_state")
    def test_rag_chat_no_docs(self, mock_rag):
        mock_state = MagicMock()
        mock_state.count.return_value = 0
        mock_rag.return_value = mock_state

        client = _get_test_client()
        r = client.post("/rag/chat", json={"session_id": "s1", "question": "Hello?"})
        assert r.status_code == 400
        assert "No documents" in r.json()["detail"]

    @patch("main.get_rag_state")
    def test_rag_chat_success(self, mock_rag):
        mock_state = MagicMock()
        mock_state.count.return_value = 10
        mock_state.chat.return_value = {
            "answer": "TLS 1.2 is enforced.",
            "context": ["chunk_a", "chunk_b", "chunk_c", "chunk_d"],
        }
        mock_rag.return_value = mock_state

        client = _get_test_client()
        r = client.post("/rag/chat", json={"session_id": "s1", "question": "What encryption?"})
        assert r.status_code == 200
        data = r.json()
        assert data["answer"] == "TLS 1.2 is enforced."
        assert len(data["used_context"]) <= 3  # capped at 3
