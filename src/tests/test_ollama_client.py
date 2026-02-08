"""
Unit tests for backend/analyzer/ollama_client.py

Covers:
  - OllamaClient initialization
  - complete_json() with mocked HTTP
  - Error handling (timeout, HTTP errors)
"""

import pytest
from unittest.mock import patch, MagicMock


def _import_client():
    from ollama_client import OllamaClient
    return OllamaClient


class TestOllamaClientInit:
    def test_default_init(self):
        Client = _import_client()
        c = Client(model="deepseek-r1")
        assert c.model == "deepseek-r1"
        assert c.base_url == "http://127.0.0.1:11434"
        assert c.timeout == 600

    def test_custom_init(self):
        Client = _import_client()
        c = Client(model="llama3", base_url="http://localhost:9999", timeout=30)
        assert c.model == "llama3"
        assert c.base_url == "http://localhost:9999"
        assert c.timeout == 30


class TestCompleteJson:
    @patch("ollama_client.requests.post")
    def test_success(self, mock_post):
        Client = _import_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": '{"compliance_state": "Fully Compliant", "confidence": 90}'}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        c = Client(model="deepseek-r1")
        result = c.complete_json(system="You are a bot.", user="Analyze this.")

        assert '"Fully Compliant"' in result
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["model"] == "deepseek-r1"
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.0
        assert payload["options"]["seed"] == 42

    @patch("ollama_client.requests.post")
    def test_empty_response(self, mock_post):
        Client = _import_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        c = Client(model="deepseek-r1")
        result = c.complete_json(system="sys", user="usr")
        assert result == ""

    @patch("ollama_client.requests.post")
    def test_http_error_raises(self, mock_post):
        Client = _import_client()
        import requests
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_post.return_value = mock_resp

        c = Client(model="deepseek-r1")
        with pytest.raises(requests.HTTPError):
            c.complete_json(system="sys", user="usr")

    @patch("ollama_client.requests.post")
    def test_timeout_raises(self, mock_post):
        Client = _import_client()
        import requests
        mock_post.side_effect = requests.Timeout("Connection timed out")

        c = Client(model="deepseek-r1")
        with pytest.raises(requests.Timeout):
            c.complete_json(system="sys", user="usr")

    @patch("ollama_client.requests.post")
    def test_payload_structure(self, mock_post):
        Client = _import_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "{}"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        c = Client(model="deepseek-r1")
        c.complete_json(system="system prompt", user="user prompt")

        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "system prompt"
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"] == "user prompt"
        assert "format" not in payload  # deepseek-r1 doesn't use format:json
