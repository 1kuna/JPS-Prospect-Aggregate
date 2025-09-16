import pytest

from app.database import db
from app.database.models import DataSource, Prospect
from app.services.llm_service import llm_service
from tests.factories import DataSourceFactory, ProspectFactory


@pytest.fixture
def prospect(app):
    """Create a persisted prospect for API tests."""
    with app.app_context():
        data_source = DataSource(**DataSourceFactory.create())
        db.session.add(data_source)
        db.session.flush()

        prospect_data = ProspectFactory.create(source_id=data_source.id)
        prospect = Prospect(**prospect_data)
        db.session.add(prospect)
        db.session.commit()

        yield prospect

        db.session.delete(prospect)
        db.session.delete(data_source)
        db.session.commit()


def test_queue_returns_503_when_llm_unavailable(monkeypatch, auth_client, prospect):
    """Queuing a prospect should fail fast when Ollama is not reachable."""
    monkeypatch.setattr(
        llm_service,
        "check_ollama_status",
        lambda timeout=5.0: {"available": False, "error": "connection refused"},
    )

    response = auth_client.post(
        "/api/llm/enhance-single",
        json={
            "prospect_id": prospect.id,
            "enhancement_type": "values",
        },
    )

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["data"]["status"] == "llm_unavailable"


def test_queue_enqueues_when_llm_available(monkeypatch, auth_client, prospect):
    """Successful queue responses should include queue metadata."""
    monkeypatch.setattr(
        llm_service,
        "check_ollama_status",
        lambda timeout=5.0: {"available": True, "model": "test-model"},
    )

    called = {}

    def fake_add_individual_enhancement(**kwargs):
        called.update(kwargs)
        return {
            "queue_item_id": "queue-123",
            "status": "queued",
            "queue_position": 1,
            "queue_size": 1,
            "was_existing": False,
        }

    monkeypatch.setattr(
        "app.api.llm_processing.add_individual_enhancement",
        fake_add_individual_enhancement,
    )

    def fake_queue_status():
        return {"worker_running": True, "queue_size": 1}

    monkeypatch.setattr(
        "app.api.llm_processing.enhancement_queue.get_queue_status",
        fake_queue_status,
    )

    response = auth_client.post(
        "/api/llm/enhance-single",
        json={
            "prospect_id": prospect.id,
            "enhancement_type": "values",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["queue_item_id"] == "queue-123"
    assert called["prospect_id"] == prospect.id
    assert called["enhancement_type"] == "values"


def test_llm_status_endpoint(admin_client, monkeypatch):
    """The status endpoint should surface queue and LLM availability information."""
    monkeypatch.setattr(
        llm_service,
        "check_ollama_status",
        lambda timeout=5.0: {"available": True, "model": "test-model"},
    )

    monkeypatch.setattr(
        "app.api.llm_processing.enhancement_queue.get_queue_status",
        lambda: {"queue_size": 0, "worker_running": False},
    )

    response = admin_client.get("/api/llm/status")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["data"]["llm_status"]["available"] is True
    assert "queue_status" in payload["data"]
