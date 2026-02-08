"""
Shared fixtures for unit and integration tests.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO

# ── Ensure backend modules are importable ──
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "backend", "analyzer"))

# ── Fake .env values used by every test ──
ENV_DEFAULTS = {
    "OLLAMA_MODEL": "deepseek-r1",
    "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
    "OLLAMA_TIMEOUT": "600",
    "OLLAMA_TEMPERATURE": "0.0",
    "OLLAMA_TOP_P": "1.0",
    "OLLAMA_NUM_PREDICT": "4096",
    "OLLAMA_SEED": "42",
    "API_PORT": "8000",
    "CORS_ORIGINS": "*",
    "CHUNK_SIZE": "1500",
    "CHUNK_OVERLAP": "200",
    "TOP_K_TEXT": "10",
    "TOP_K_TABLE": "6",
    "RAG_CHUNK_SIZE": "1000",
    "RAG_CHUNK_OVERLAP": "150",
    "RAG_SIMILARITY_K": "4",
    "API_BASE": "http://127.0.0.1:8000",
    "ANALYZE_TIMEOUT": "300",
    "CHAT_TIMEOUT": "120",
}


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Inject all required env vars so modules never blow up on import."""
    for k, v in ENV_DEFAULTS.items():
        monkeypatch.setenv(k, v)


@pytest.fixture
def sample_pdf_bytes():
    """
    Build a minimal valid PDF in memory with reportlab (if available)
    or fall back to a hand-crafted tiny PDF.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.drawString(100, 700, "Section 3.1 Password Policy")
        c.drawString(100, 680, "All passwords must be at least 12 characters.")
        c.drawString(100, 660, "Passwords shall be stored using salted hashing.")
        c.drawString(100, 640, "Account lockout after 5 failed attempts.")
        c.drawString(100, 620, "Section 4.2 Encryption")
        c.drawString(100, 600, "All data in transit encrypted via TLS 1.2 or higher.")
        c.save()
        return buf.getvalue()
    except ImportError:
        # Minimal hand-crafted PDF (1 page, some text)
        return (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
            b"/Contents 4 0 R>>endobj\n"
            b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td "
            b"(Password Policy) Tj ET\nendstream\nendobj\n"
            b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n"
            b"0000000058 00000 n \n0000000115 00000 n \n0000000214 00000 n \n"
            b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n309\n%%EOF"
        )


@pytest.fixture
def mock_ollama_client():
    """Return a MagicMock that behaves like OllamaClient."""
    client = MagicMock()
    client.model = "deepseek-r1"
    client.base_url = "http://127.0.0.1:11434"
    client.timeout = 600
    return client


@pytest.fixture
def sample_llm_json_response():
    """A realistic raw LLM response with <think> wrapper."""
    return (
        '<think>\nLet me analyze the contract for password management.\n'
        'Sub-requirement 1: YES — Section 3.1 defines password length.\n'
        '</think>\n'
        '```json\n'
        '{\n'
        '  "compliance_state": "Partially Compliant",\n'
        '  "confidence": 57,\n'
        '  "relevant_quotes": ["Section 3.1 (Password Policy)", "Exhibit G (ID-01)"],\n'
        '  "rationale": "The contract addresses password length and storage but lacks '
        'provisions for credential vaulting and time-based rotation."\n'
        '}\n'
        '```'
    )


@pytest.fixture
def sample_clean_json():
    """A clean JSON string (no wrappers)."""
    return (
        '{"compliance_state": "Fully Compliant", "confidence": 92, '
        '"relevant_quotes": ["Section 4.2"], '
        '"rationale": "All data in transit encryption requirements are explicitly addressed '
        'including TLS 1.2+ and certificate management."}'
    )
