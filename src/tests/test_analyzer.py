"""
Unit tests for backend/analyzer/analyzer.py

Covers:
  - _strip_wrappers()
  - _apply_policy()
  - _parse_llm_json()
  - _analyze_single_question()  (mocked LLM)
  - analyze_pdf_bytes()          (mocked LLM + PDF)
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


# ── Helpers to import with env already set (autouse fixture in conftest) ──
def _import_analyzer():
    from analyzer import (
        _strip_wrappers, _apply_policy, _parse_llm_json,
        _analyze_single_question, analyze_pdf_bytes,
        ComplianceResult, ALLOWED_STATES,
    )
    return (
        _strip_wrappers, _apply_policy, _parse_llm_json,
        _analyze_single_question, analyze_pdf_bytes,
        ComplianceResult, ALLOWED_STATES,
    )


# ═══════════════════════════════════════════
#  _strip_wrappers
# ═══════════════════════════════════════════
class TestStripWrappers:
    def test_removes_think_tags(self):
        fn = _import_analyzer()[0]
        raw = "<think>some reasoning</think>\n{\"key\": \"value\"}"
        assert "<think>" not in fn(raw)
        assert '{"key": "value"}' == fn(raw)

    def test_removes_code_fences(self):
        fn = _import_analyzer()[0]
        raw = '```json\n{"a": 1}\n```'
        assert fn(raw) == '{"a": 1}'

    def test_removes_both_think_and_fences(self):
        fn = _import_analyzer()[0]
        raw = '<think>blah</think>\n```json\n{"x": 2}\n```'
        assert fn(raw) == '{"x": 2}'

    def test_empty_string(self):
        fn = _import_analyzer()[0]
        assert fn("") == ""

    def test_none_passthrough(self):
        fn = _import_analyzer()[0]
        assert fn(None) is None

    def test_no_wrappers(self):
        fn = _import_analyzer()[0]
        raw = '{"plain": true}'
        assert fn(raw) == '{"plain": true}'

    def test_multiline_think(self):
        fn = _import_analyzer()[0]
        raw = "<think>\nline1\nline2\n</think>\nresult"
        assert fn(raw) == "result"


# ═══════════════════════════════════════════
#  _apply_policy
# ═══════════════════════════════════════════
class TestApplyPolicy:
    def test_low_confidence_non_compliant(self):
        fn = _import_analyzer()[1]
        state, conf = fn("Fully Compliant", 20)
        assert state == "Non-Compliant"
        assert conf == 20

    def test_mid_confidence_partially_compliant(self):
        fn = _import_analyzer()[1]
        state, conf = fn("Fully Compliant", 60)
        assert state == "Partially Compliant"
        assert conf == 60

    def test_high_confidence_keeps_valid_state(self):
        fn = _import_analyzer()[1]
        state, conf = fn("Fully Compliant", 92)
        assert state == "Fully Compliant"
        assert conf == 92

    def test_high_confidence_invalid_state_defaults(self):
        fn = _import_analyzer()[1]
        state, conf = fn("Invalid State", 90)
        assert state == "Fully Compliant"
        assert conf == 90

    def test_boundary_40(self):
        fn = _import_analyzer()[1]
        state, conf = fn("Non-Compliant", 40)
        assert state == "Partially Compliant"
        assert conf == 40

    def test_boundary_85(self):
        fn = _import_analyzer()[1]
        state, conf = fn("Fully Compliant", 85)
        assert state == "Fully Compliant"
        assert conf == 85

    def test_boundary_39(self):
        fn = _import_analyzer()[1]
        state, conf = fn("Partially Compliant", 39)
        assert state == "Non-Compliant"
        assert conf == 39

    def test_clamp_to_98(self):
        fn = _import_analyzer()[1]
        state, conf = fn("Fully Compliant", 150)
        assert conf == 98

    def test_clamp_to_0(self):
        fn = _import_analyzer()[1]
        state, conf = fn("Non-Compliant", -10)
        assert conf == 0
        assert state == "Non-Compliant"

    def test_boundary_84(self):
        fn = _import_analyzer()[1]
        state, conf = fn("Fully Compliant", 84)
        assert state == "Partially Compliant"
        assert conf == 84


# ═══════════════════════════════════════════
#  _parse_llm_json
# ═══════════════════════════════════════════
class TestParseLlmJson:
    def test_clean_json(self, sample_clean_json):
        fn = _import_analyzer()[2]
        result = fn(sample_clean_json)
        assert result["compliance_state"] == "Fully Compliant"
        assert result["confidence"] == 92

    def test_json_with_think_wrapper(self, sample_llm_json_response):
        fn = _import_analyzer()[2]
        result = fn(sample_llm_json_response)
        assert result["compliance_state"] == "Partially Compliant"
        assert result["confidence"] == 57
        assert len(result["relevant_quotes"]) == 2

    def test_no_json_raises(self):
        fn = _import_analyzer()[2]
        with pytest.raises(Exception):
            fn("This has no JSON at all.")

    def test_malformed_json_repaired(self):
        fn = _import_analyzer()[2]
        # Missing closing quote, trailing comma
        raw = '{"state": "ok", "val": 42,}'
        result = fn(raw)
        assert result["val"] == 42

    def test_nested_think_and_fences(self):
        fn = _import_analyzer()[2]
        raw = (
            "<think>reasoning</think>\n"
            "```json\n"
            '{"compliance_state": "Non-Compliant", "confidence": 10, '
            '"relevant_quotes": [], "rationale": "Nothing found in the contract text."}\n'
            "```"
        )
        result = fn(raw)
        assert result["compliance_state"] == "Non-Compliant"
        assert result["confidence"] == 10


# ═══════════════════════════════════════════
#  _analyze_single_question  (mocked LLM)
# ═══════════════════════════════════════════
class TestAnalyzeSingleQuestion:
    def test_empty_context_returns_non_compliant(self, mock_ollama_client):
        fn = _import_analyzer()[3]
        result = fn(mock_ollama_client, "Password Management", "")
        assert result["compliance_state"] == "Non-Compliant"
        assert result["confidence"] == 0
        assert result["relevant_quotes"] == []
        mock_ollama_client.complete_json.assert_not_called()

    def test_whitespace_context_returns_non_compliant(self, mock_ollama_client):
        fn = _import_analyzer()[3]
        result = fn(mock_ollama_client, "Password Management", "   \n  ")
        assert result["compliance_state"] == "Non-Compliant"
        assert result["confidence"] == 0

    def test_valid_response_parsed(self, mock_ollama_client, sample_llm_json_response):
        fn = _import_analyzer()[3]
        mock_ollama_client.complete_json.return_value = sample_llm_json_response
        result = fn(mock_ollama_client, "Password Management", "Section 3.1 Password Policy ...")
        assert result["compliance_state"] == "Partially Compliant"
        assert 0 <= result["confidence"] <= 100

    def test_llm_error_returns_non_compliant(self, mock_ollama_client):
        fn = _import_analyzer()[3]
        mock_ollama_client.complete_json.side_effect = Exception("Connection refused")
        result = fn(mock_ollama_client, "IT Asset Management", "Some context")
        assert result["compliance_state"] == "Non-Compliant"
        assert result["confidence"] == 0
        assert "Error analyzing" in result["rationale"]

    def test_quotes_as_dicts_normalized(self, mock_ollama_client):
        fn = _import_analyzer()[3]
        raw = (
            '{"compliance_state": "Partially Compliant", "confidence": 50, '
            '"relevant_quotes": [{"section": "3.1", "text": "Password length"}], '
            '"rationale": "The contract partially covers password management requirements."}'
        )
        mock_ollama_client.complete_json.return_value = raw
        result = fn(mock_ollama_client, "Password Management", "Some contract text")
        # Should be normalized to string like "Section 3.1: Password length"
        assert any("3.1" in q for q in result["relevant_quotes"])

    def test_confidence_as_string_percentage(self, mock_ollama_client):
        fn = _import_analyzer()[3]
        raw = (
            '{"compliance_state": "Partially Compliant", "confidence": "71.4%", '
            '"relevant_quotes": [], '
            '"rationale": "The contract has 5 out of 7 sub-requirements addressed clearly."}'
        )
        mock_ollama_client.complete_json.return_value = raw
        result = fn(mock_ollama_client, "Password Management", "Some context here")
        assert isinstance(result["confidence"], int)


# ═══════════════════════════════════════════
#  analyze_pdf_bytes  (mocked everything)
# ═══════════════════════════════════════════
class TestAnalyzePdfBytes:
    @patch("analyzer.OllamaClient")
    @patch("analyzer.load_docs_from_pdf_bytes")
    def test_returns_five_results(self, mock_load, mock_client_cls):
        fn = _import_analyzer()[4]
        # Mock PDF extraction
        mock_load.return_value = [
            Document(page_content="Password policy section", metadata={"page": 1, "type": "page"}),
            Document(page_content="TLS encryption section", metadata={"page": 2, "type": "page"}),
        ]
        # Mock LLM responses
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.complete_json.return_value = (
            '{"compliance_state": "Partially Compliant", "confidence": 50, '
            '"relevant_quotes": ["Section 3.1"], '
            '"rationale": "The contract partially addresses the requirements in this compliance area."}'
        )
        results = fn(b"fake-pdf-bytes", "deepseek-r1")
        assert len(results) == 5
        for r in results:
            assert "compliance_state" in r
            assert "confidence" in r

    @patch("analyzer.OllamaClient")
    @patch("analyzer.load_docs_from_pdf_bytes")
    def test_empty_pdf_all_non_compliant(self, mock_load, mock_client_cls):
        fn = _import_analyzer()[4]
        mock_load.return_value = []
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        results = fn(b"fake-pdf-bytes", "deepseek-r1")
        assert len(results) == 5
        for r in results:
            assert r["compliance_state"] == "Non-Compliant"
            assert r["confidence"] == 0
