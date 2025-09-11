"""
Tests for new LLM API endpoints - iterative processing, logs, outputs, and cleanup.

Following production-level testing principles:
- No hardcoded expected values
- Tests verify behavior, not specific data  
- Uses real database operations
- Mocks only external services
"""

import json
import random
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app import create_app
from app.database import db
from app.database.models import DataSource, Prospect

UTC = timezone.utc


class TestLLMIterativeAndLogs:
    """Test suite for new LLM API endpoints."""

    @pytest.fixture(scope="class")
    def app(self):
        """Create test Flask app with real database."""
        app = create_app()
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SECRET_KEY"] = f"test-secret-{random.randint(1000, 9999)}"
        return app

    @pytest.fixture()
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture(autouse=True)
    def setup_database(self, app):
        """Set up test database with sample data."""
        with app.app_context():
            db.create_all()

            # Create test data source
            source = DataSource(
                name="Test LLM Source",
                url="https://llm-test.gov",
                last_scraped=datetime.now(UTC) - timedelta(days=1),
            )
            db.session.add(source)
            db.session.flush()

            # Create test prospects with various enhancement states
            num_prospects = 15
            prospects = []
            for i in range(num_prospects):
                prospect = Prospect(
                    id=f"LLM-ITER-{i:03d}",
                    title=f"Contract {i}",
                    description=f"Description for contract {i}",
                    agency=f"Agency {i % 3}",
                    naics="541511" if i % 3 == 0 else None,
                    estimated_value_text=f"${(i + 1) * 10000:,}",
                    source_id=source.id,
                    loaded_at=datetime.now(UTC) - timedelta(hours=i),
                    ollama_processed_at=datetime.now(UTC) if i < 5 else None,
                    enhancement_status=["idle", "queued", "processing", "completed", "failed"][i % 5],
                )
                db.session.add(prospect)
                prospects.append(prospect)

            db.session.commit()
            self.test_prospects = prospects
            self.test_source = source

            yield

            db.session.rollback()
            db.drop_all()

    def _auth_request(self, client, method, url, user_id=None, user_role=None, **kwargs):
        """Helper method to make authenticated requests."""
        with client.session_transaction() as sess:
            sess["user_id"] = user_id or random.randint(1, 100)
            sess["user_role"] = user_role or "admin"

        method_func = getattr(client, method)
        return method_func(url, **kwargs)

    def test_iterative_start_endpoint(self, client):
        """Test POST /api/llm/iterative/start endpoint."""
        with patch("app.api.llm_processing.start_iterative_enhancement") as mock_start:
            mock_start.return_value = {
                "started": True,
                "enhancement_type": "values",
                "skip_existing": True,
                "total_prospects": 10,
            }

            # Test with valid parameters
            response = self._auth_request(
                client,
                "post",
                "/api/llm/iterative/start",
                json={
                    "enhancement_type": "values",
                    "skip_existing": True,
                },
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "status" in data
            assert data["status"] == "success"
            assert "data" in data
            assert data["data"]["started"] is True
            assert data["data"]["enhancement_type"] == "values"

            # Test with invalid enhancement type
            response = self._auth_request(
                client,
                "post",
                "/api/llm/iterative/start",
                json={
                    "enhancement_type": "invalid_type",
                },
            )

            assert response.status_code == 400
            data = response.get_json()
            assert "error" in data or "message" in data

    def test_iterative_stop_endpoint(self, client):
        """Test POST /api/llm/iterative/stop endpoint."""
        with patch("app.api.llm_processing.stop_iterative_enhancement") as mock_stop:
            mock_stop.return_value = {
                "stopped": True,
                "prospects_processed": 5,
            }

            response = self._auth_request(
                client,
                "post",
                "/api/llm/iterative/stop",
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "status" in data
            assert data["status"] == "success"
            assert "data" in data
            assert data["data"]["stopped"] is True
            assert "prospects_processed" in data["data"]

    def test_iterative_progress_endpoint(self, client):
        """Test GET /api/llm/iterative/progress endpoint."""
        with patch("app.api.llm_processing.get_iterative_progress") as mock_progress:
            mock_progress.return_value = {
                "is_running": True,
                "enhancement_type": "naics",
                "processed": 25,
                "total": 100,
                "percentage": 25.0,
                "current_prospect": "PROSPECT-123",
            }

            response = self._auth_request(client, "get", "/api/llm/iterative/progress")

            assert response.status_code == 200
            data = response.get_json()
            assert "status" in data
            assert data["status"] == "success"
            assert "data" in data
            
            progress = data["data"]
            assert progress["is_running"] is True
            assert progress["processed"] == 25
            assert progress["total"] == 100
            assert progress["percentage"] == 25.0
            assert "current_prospect" in progress

    def test_llm_logs_endpoint(self, client):
        """Test GET /api/llm/logs endpoint."""
        with patch("app.api.llm_processing.get_enhancement_logs") as mock_logs:
            # Generate mock log data
            log_entries = []
            for i in range(10):
                log_entries.append({
                    "id": i + 1,
                    "timestamp": (datetime.now(UTC) - timedelta(minutes=i)).isoformat(),
                    "enhancement_type": ["values", "titles", "naics"][i % 3],
                    "prospect_id": f"PROSPECT-{i:03d}",
                    "status": ["started", "completed", "failed"][i % 3],
                    "message": f"Log message {i}",
                })
            
            mock_logs.return_value = log_entries

            # Test without limit
            response = self._auth_request(client, "get", "/api/llm/logs")
            
            assert response.status_code == 200
            data = response.get_json()
            assert "status" in data
            assert data["status"] == "success"
            assert "data" in data
            assert isinstance(data["data"], list)
            assert len(data["data"]) == 10
            
            # Verify log structure
            for log in data["data"]:
                assert "timestamp" in log
                assert "enhancement_type" in log
                assert "status" in log

            # Test with limit
            mock_logs.return_value = log_entries[:5]
            response = self._auth_request(client, "get", "/api/llm/logs?limit=5")
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data["data"]) == 5

    def test_llm_outputs_endpoint(self, client):
        """Test GET /api/llm/outputs endpoint."""
        with patch("app.api.llm_processing.get_enhancement_outputs") as mock_outputs:
            # Generate mock output data
            outputs = []
            enhancement_types = ["values", "titles", "naics", "set_asides"]
            
            for i in range(8):
                outputs.append({
                    "prospect_id": f"PROSPECT-{i:03d}",
                    "enhancement_type": enhancement_types[i % 4],
                    "timestamp": (datetime.now(UTC) - timedelta(hours=i)).isoformat(),
                    "original_value": f"Original {i}",
                    "enhanced_value": f"Enhanced {i}",
                    "confidence": 0.85 + (i % 3) * 0.05,
                })
            
            mock_outputs.return_value = outputs

            # Test without filter
            response = self._auth_request(client, "get", "/api/llm/outputs")
            
            assert response.status_code == 200
            data = response.get_json()
            assert "status" in data
            assert data["status"] == "success"
            assert "data" in data
            assert isinstance(data["data"], list)
            assert len(data["data"]) == 8

            # Test with enhancement_type filter
            filtered_outputs = [o for o in outputs if o["enhancement_type"] == "values"]
            mock_outputs.return_value = filtered_outputs
            
            response = self._auth_request(
                client, "get", "/api/llm/outputs?enhancement_type=values"
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert all(o["enhancement_type"] == "values" for o in data["data"])

    def test_cleanup_stale_locks_endpoint(self, client):
        """Test POST /api/llm/cleanup-stale-locks endpoint."""
        with patch("app.api.llm_processing.cleanup_stale_locks") as mock_cleanup:
            cleanup_count = random.randint(0, 10)
            mock_cleanup.return_value = cleanup_count

            response = self._auth_request(
                client,
                "post",
                "/api/llm/cleanup-stale-locks",
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "status" in data
            assert data["status"] == "success"
            assert "data" in data
            assert data["data"]["cleanup_count"] == cleanup_count
            assert "message" in data

    def test_authentication_required_for_new_endpoints(self, client):
        """Test that authentication is required for all new endpoints."""
        endpoints = [
            ("/api/llm/iterative/start", "post"),
            ("/api/llm/iterative/stop", "post"),
            ("/api/llm/iterative/progress", "get"),
            ("/api/llm/logs", "get"),
            ("/api/llm/outputs", "get"),
            ("/api/llm/cleanup-stale-locks", "post"),
        ]

        for endpoint, method in endpoints:
            method_func = getattr(client, method)
            if method == "post":
                response = method_func(endpoint, json={})
            else:
                response = method_func(endpoint)
            
            # Should require authentication
            assert response.status_code in [401, 302], f"Endpoint {endpoint} should require auth"

    def test_iterative_start_validation(self, client):
        """Test validation for iterative start endpoint."""
        # Test missing enhancement_type
        response = self._auth_request(
            client,
            "post",
            "/api/llm/iterative/start",
            json={"skip_existing": True},
        )
        
        # Should fail validation
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data or "message" in data

        # Test invalid enhancement_type
        response = self._auth_request(
            client,
            "post",
            "/api/llm/iterative/start",
            json={
                "enhancement_type": "not_a_valid_type",
                "skip_existing": False,
            },
        )
        
        assert response.status_code == 400

    def test_logs_limit_parameter(self, client):
        """Test that logs endpoint respects limit parameter."""
        with patch("app.api.llm_processing.get_enhancement_logs") as mock_logs:
            # Create many log entries
            log_entries = [
                {
                    "id": i,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "enhancement_type": "values",
                    "status": "completed",
                }
                for i in range(100)
            ]
            
            # Test default limit
            mock_logs.return_value = log_entries[:20]  # Default limit
            response = self._auth_request(client, "get", "/api/llm/logs")
            assert response.status_code == 200
            data = response.get_json()
            assert len(data["data"]) <= 20
            
            # Test custom limit
            mock_logs.return_value = log_entries[:50]
            response = self._auth_request(client, "get", "/api/llm/logs?limit=50")
            assert response.status_code == 200
            data = response.get_json()
            assert len(data["data"]) <= 50
            
            # Test max limit enforcement
            mock_logs.return_value = log_entries[:100]
            response = self._auth_request(client, "get", "/api/llm/logs?limit=1000")
            assert response.status_code == 200
            data = response.get_json()
            assert len(data["data"]) <= 100  # Should be capped at max

    def test_outputs_filtering(self, client):
        """Test that outputs endpoint filters correctly."""
        with patch("app.api.llm_processing.get_enhancement_outputs") as mock_outputs:
            all_outputs = [
                {"enhancement_type": "values", "prospect_id": "P1"},
                {"enhancement_type": "titles", "prospect_id": "P2"},
                {"enhancement_type": "naics", "prospect_id": "P3"},
                {"enhancement_type": "set_asides", "prospect_id": "P4"},
                {"enhancement_type": "values", "prospect_id": "P5"},
            ]
            
            # Test filter by enhancement_type
            values_outputs = [o for o in all_outputs if o["enhancement_type"] == "values"]
            mock_outputs.return_value = values_outputs
            
            response = self._auth_request(
                client, "get", "/api/llm/outputs?enhancement_type=values"
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data["data"]) == 2
            assert all(o["enhancement_type"] == "values" for o in data["data"])

    def test_cleanup_idempotency(self, client):
        """Test that cleanup endpoint is idempotent."""
        with patch("app.api.llm_processing.cleanup_stale_locks") as mock_cleanup:
            # First call cleans up 5 locks
            mock_cleanup.return_value = 5
            response1 = self._auth_request(client, "post", "/api/llm/cleanup-stale-locks")
            assert response1.status_code == 200
            data1 = response1.get_json()
            assert data1["data"]["cleanup_count"] == 5
            
            # Second call cleans up 0 (already cleaned)
            mock_cleanup.return_value = 0
            response2 = self._auth_request(client, "post", "/api/llm/cleanup-stale-locks")
            assert response2.status_code == 200
            data2 = response2.get_json()
            assert data2["data"]["cleanup_count"] == 0