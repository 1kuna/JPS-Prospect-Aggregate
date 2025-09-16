from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_service import LLMService

@pytest.fixture
def service():
    return LLMService(model_name="test-model", batch_size=5)


def test_check_ollama_status_available(service, monkeypatch):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.content = b"{}"
    response.json.return_value = {"models": [{"name": "test-model"}]}

    monkeypatch.setattr(
        "app.services.llm_service.requests.get", lambda *args, **kwargs: response
    )

    status = service.check_ollama_status()
    assert status["available"] is True
    assert "test-model" in status["installed_models"]


def test_check_ollama_status_unavailable(service, monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise ConnectionError("connection refused")

    monkeypatch.setattr("app.services.llm_service.requests.get", raise_connection_error)

    status = service.check_ollama_status()
    assert status["available"] is False
    assert "connection refused" in status["error"]


@patch("app.services.llm_service.call_ollama")
def test_parse_contract_value_with_llm_success(mock_call, service):
    mock_call.return_value = json.dumps({"single": 100000, "min": 90000, "max": 110000})

    result = service.parse_contract_value_with_llm("$100k", prospect_id="TEST-1")

    assert result["single"] == 100000.0
    assert result["min"] == 90000.0
    assert result["max"] == 110000.0


@patch("app.services.llm_service.call_ollama")
def test_parse_contract_value_with_llm_empty_response(mock_call, service, caplog):
    mock_call.return_value = ""

    result = service.parse_contract_value_with_llm("TBD", prospect_id="TEST-2")

    assert result["single"] is None
    assert result["confidence"] == 0.0
    assert (
        any(
            "Empty response" in record.message
            for record in caplog.records
            if record.levelname == "ERROR"
        )
        is False
    )
