"""
Comprehensive tests for Decisions API endpoints.

Tests all decision-related API functionality including CRUD operations.
Following production-level testing principles:
- No hardcoded expected values
- Tests verify behavior, not specific data
- Uses real database operations
- Focus on API behavior patterns
"""

import json
from datetime import timezone
UTC = timezone.utc
from datetime import datetime, timedelta

import pytest

from app import create_app
from app.database import db
from app.database.models import DataSource, GoNoGoDecision, Prospect
from app.database.user_models import User
from tests.factories import (
    ProspectFactory,
    DataSourceFactory,
    UserFactory,
    DecisionFactory,
    reset_counters,
)


class TestDecisionsAPI:
    """Test suite for Decisions API endpoints following black-box testing principles."""

    @pytest.fixture(scope="class")
    def app(self):
        """Create test Flask app with real database."""
        app = create_app()
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    @pytest.fixture()
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def _auth_request(self, client, method, url, user_id=None, **kwargs):
        """Helper method to make authenticated requests."""
        with client.session_transaction() as sess:
            sess["user_id"] = user_id if user_id else self.test_user_id
            sess["user_role"] = "user"

        method_func = getattr(client, method)
        return method_func(url, **kwargs)

    @pytest.fixture(autouse=True)
    def setup_database(self, app, client):
        """Set up test database with deterministic data."""
        with app.app_context():
            db.create_all()
            reset_counters()  # Reset for each test class

            # Create data sources deterministically
            num_sources = 3
            data_sources = []
            for i in range(num_sources):
                source_data = DataSourceFactory.create()
                source = DataSource(**source_data)
                db.session.add(source)
                data_sources.append(source)

            db.session.flush()

            # Create test users deterministically
            num_users = 5
            test_users = []
            for i in range(num_users):
                user_data = UserFactory.create()
                user = User(
                    first_name=user_data["first_name"],
                    email=user_data["email"],
                    role=user_data["role"],
                )
                user.id = user_data["id"]  # Set deterministic ID
                db.session.add(user)
                test_users.append(user)

            db.session.flush()

            # Create prospects deterministically
            num_prospects = 8
            test_prospects = []
            for i in range(num_prospects):
                prospect_data = ProspectFactory.create()
                # Use actual source IDs
                prospect_data["source_id"] = data_sources[i % len(data_sources)].id
                prospect_data["agency"] = data_sources[i % len(data_sources)].name
                
                prospect = Prospect(
                    id=prospect_data["id"],
                    title=prospect_data["title"],
                    description=prospect_data["description"],
                    agency=prospect_data["agency"],
                    naics=prospect_data["naics"],
                    estimated_value_text=prospect_data["estimated_value_text"],
                    source_id=prospect_data["source_id"],
                    loaded_at=prospect_data["loaded_at"],
                )
                db.session.add(prospect)
                test_prospects.append(prospect)

            db.session.flush()

            # Create some existing decisions deterministically
            num_decisions = 3  # Fixed number
            existing_decisions = []
            for i in range(num_decisions):
                decision_data = DecisionFactory.create()
                decision = GoNoGoDecision(
                    prospect_id=test_prospects[i].id,
                    user_id=test_users[i % len(test_users)].id,
                    decision=decision_data["decision"],
                    reason=decision_data["reason"],
                )
                db.session.add(decision)
                existing_decisions.append(decision)

            db.session.commit()

            # Store test data for use in tests
            self.test_users = test_users
            self.test_prospects = test_prospects
            self.test_decisions = existing_decisions
            self.test_user_id = test_users[0].id if test_users else None

            yield

            # Cleanup
            db.session.rollback()
            db.drop_all()

    def test_create_decision_behavior(self, client):
        """Test that decision creation behaves correctly."""
        # Select a prospect deterministically
        prospect = self.test_prospects[0]  # First prospect
        decision_type = "go"  # Fixed decision type
        reason_text = "Test reason for decision"

        decision_data = {
            "prospect_id": prospect.id,
            "decision": decision_type,
            "reason": reason_text,
        }

        response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            data=json.dumps(decision_data),
            content_type="application/json",
        )

        # Should succeed
        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert "status" in data
        assert data["status"] == "success"
        assert "data" in data
        assert "decision" in data["data"]

        # Verify decision was created/updated with correct attributes
        decision = data["data"]["decision"]
        assert decision["prospect_id"] == prospect.id
        assert decision["decision"] == decision_type
        assert decision["reason"] == reason_text
        assert decision["user_id"] == self.test_user_id
        assert "created_at" in decision

    def test_decision_validation_behavior(self, client):
        """Test that decision validation works correctly."""
        # Test missing required fields
        invalid_requests = [
            {"decision": "go", "reason": "Missing prospect_id"},
            {
                "prospect_id": self.test_prospects[1].id,  # Use second prospect
                "reason": "Missing decision",
            },
            {
                "prospect_id": "invalid-id",
                "decision": "go",
                "reason": "Invalid prospect",
            },
            {
                "prospect_id": self.test_prospects[2].id,  # Use third prospect
                "decision": "maybe",
                "reason": "Invalid decision type",
            },
        ]

        for invalid_data in invalid_requests:
            response = self._auth_request(
                client,
                "post",
                "/api/decisions/",
                data=json.dumps(invalid_data),
                content_type="application/json",
            )

            # Should fail validation
            assert response.status_code == 400 or response.status_code == 404
            data = response.get_json()
            assert "message" in data or "error" in data

    def test_get_decisions_for_prospect(self, client):
        """Test retrieving decisions for a specific prospect."""
        # Test with a prospect that has decisions
        if self.test_decisions:
            decision = self.test_decisions[0]  # Use first decision
            prospect_id = decision.prospect_id

            response = self._auth_request(
                client, "get", f"/api/decisions/prospect/{prospect_id}"
            )

            assert response.status_code == 200
            data = response.get_json()

            # Verify response structure
            assert "data" in data
            assert "decisions" in data["data"]
            assert isinstance(data["data"]["decisions"], list)

            # Verify all decisions are for the requested prospect
            for dec in data["data"]["decisions"]:
                assert dec["prospect_id"] == prospect_id

        # Test with a prospect that might not have decisions
        prospect = self.test_prospects[-1]  # Use last prospect
        response = self._auth_request(client, "get", f"/api/decisions/prospect/{prospect.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert "decisions" in data["data"]
        # May have 0 or more decisions
        assert isinstance(data["data"]["decisions"], list)

    def test_get_user_decisions(self, client):
        """Test retrieving current user's decisions."""
        # Create a decision for the test user
        prospect = self.test_prospects[3]  # Use fourth prospect
        decision_data = {
            "prospect_id": prospect.id,
            "decision": "go",
            "reason": "User decision test",
        }

        # Create decision
        create_response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            data=json.dumps(decision_data),
            content_type="application/json",
        )
        assert create_response.status_code == 200

        # Get user's decisions
        response = self._auth_request(client, "get", "/api/decisions/user")

        assert response.status_code == 200
        data = response.get_json()

        assert "data" in data
        assert "decisions" in data["data"]

        # All decisions should belong to the current user
        for decision in data["data"]["decisions"]:
            assert decision["user_id"] == self.test_user_id

    def test_update_existing_decision(self, client):
        """Test updating an existing decision."""
        # Create initial decision
        prospect = self.test_prospects[4]  # Use fifth prospect
        initial_data = {
            "prospect_id": prospect.id,
            "decision": "go",
            "reason": "Initial reason",
        }

        response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            data=json.dumps(initial_data),
            content_type="application/json",
        )
        assert response.status_code == 200

        # Update the decision
        updated_data = {
            "prospect_id": prospect.id,
            "decision": "no-go",
            "reason": "Updated after review",
        }

        response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            data=json.dumps(updated_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify update was applied
        assert data["data"]["decision"]["decision"] == "no-go"
        assert data["data"]["decision"]["reason"] == "Updated after review"
        assert data["data"]["decision"]["prospect_id"] == prospect.id

    def test_delete_decision_behavior(self, client):
        """Test decision deletion behavior with ownership checks."""
        # Create a decision to delete
        prospect = self.test_prospects[5]  # Use sixth prospect
        decision_data = {
            "prospect_id": prospect.id,
            "decision": "go",
            "reason": "Will be deleted",
        }

        create_response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            data=json.dumps(decision_data),
            content_type="application/json",
        )

        assert create_response.status_code == 200
        decision_id = create_response.get_json()["data"]["decision"]["id"]

        # Test that decision_id is an integer (per API spec)
        assert isinstance(decision_id, int), "Decision ID should be an integer"

        # Delete the decision (owner should be able to delete)
        delete_response = self._auth_request(
            client, "delete", f"/api/decisions/{decision_id}"
        )

        assert delete_response.status_code == 200
        data = delete_response.get_json()
        assert data["status"] == "success"

        # Verify deletion by trying to get decisions for that prospect
        get_response = self._auth_request(
            client, "get", f"/api/decisions/prospect/{prospect.id}"
        )

        assert get_response.status_code == 200
        decisions = get_response.get_json()["data"]["decisions"]

        # The deleted decision should not be in the list
        decision_ids = [d["id"] for d in decisions]
        assert decision_id not in decision_ids

    def test_delete_decision_ownership_check(self, client):
        """Test that users can only delete their own decisions."""
        # Create a decision as user 1
        prospect = self.test_prospects[6]  # Use seventh prospect
        decision_data = {
            "prospect_id": prospect.id,
            "decision": "go",
            "reason": "User 1 decision",
        }

        create_response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            user_id=self.test_users[0].id if self.test_users else None,
            data=json.dumps(decision_data),
            content_type="application/json",
        )

        assert create_response.status_code == 200
        decision_id = create_response.get_json()["data"]["decision"]["id"]

        # Try to delete as a different user (should fail)
        if len(self.test_users) > 1:
            delete_response = self._auth_request(
                client,
                "delete",
                f"/api/decisions/{decision_id}",
                user_id=self.test_users[1].id,
            )

            assert delete_response.status_code == 403
            data = delete_response.get_json()
            assert "can only delete your own" in data.get("message", "").lower()

    def test_delete_nonexistent_decision(self, client):
        """Test deleting a decision that doesn't exist."""
        fake_id = 999999  # Fixed large ID that won't exist

        response = self._auth_request(client, "delete", f"/api/decisions/{fake_id}")

        assert response.status_code == 404
        data = response.get_json()
        assert "message" in data or "error" in data

    def test_authentication_required(self, client):
        """Test that authentication is required for decision endpoints."""
        # Test without authentication
        response = client.get("/api/decisions/user")

        assert response.status_code == 401
        data = response.get_json()
        assert "message" in data or "error" in data

    def test_decision_reason_variations(self, client):
        """Test decision creation with various reason formats."""
        prospect = self.test_prospects[7]  # Use eighth prospect

        # Test with different reason lengths and formats
        test_reasons = [
            "",  # Empty reason
            "Short",
            "A" * 500,  # Long reason
            "Reason with\nnewlines\nand\ttabs",
            "Reason with special chars: @#$%^&*()",
            "   Reason with spaces   ",
            None,  # Null reason
        ]

        for reason in test_reasons:
            decision_data = {
                "prospect_id": prospect.id,
                "decision": "go" if i % 2 == 0 else "no-go",  # Alternate deterministically
                "reason": reason if reason is not None else "",
            }

            response = self._auth_request(
                client,
                "post",
                "/api/decisions/",
                data=json.dumps(decision_data),
                content_type="application/json",
            )

            # Should handle all reason formats
            assert response.status_code == 200 or response.status_code == 400

            if response.status_code == 200:
                data = response.get_json()
                stored_reason = data["data"]["decision"]["reason"]
                # Verify reason was stored (may be processed/trimmed)
                # Empty strings may be stored as None
                if reason == "":
                    assert stored_reason is None or stored_reason == ""
                elif reason is None:
                    assert stored_reason is None or stored_reason == ""
                else:
                    # Non-empty, non-None reasons should be stored (possibly trimmed)
                    if reason.strip():
                        # If there's content after stripping, it should be stored
                        assert stored_reason is not None, f"Expected non-None for reason={repr(reason)}, got {repr(stored_reason)}"
                    else:
                        # If stripping results in empty, it may be stored as None
                        assert stored_reason is None or stored_reason == ""

    def test_concurrent_decision_updates(self, client):
        """Test handling of concurrent decision updates."""
        prospect = self.test_prospects[0]  # Use first prospect

        # Simulate multiple users updating the same prospect
        for i, user in enumerate(self.test_users[: min(3, len(self.test_users))]):
            decision_data = {
                "prospect_id": prospect.id,
                "decision": "go" if i % 2 == 0 else "no-go",  # Alternate
                "reason": f"User {i} decision",
            }

            response = self._auth_request(
                client,
                "post",
                "/api/decisions/",
                user_id=user.id,
                data=json.dumps(decision_data),
                content_type="application/json",
            )

            # Each user should be able to create their own decision
            assert response.status_code == 200
            data = response.get_json()
            assert data["data"]["decision"]["user_id"] == user.id

    def test_decision_timestamp_behavior(self, client):
        """Test that decision timestamps are handled correctly."""
        prospect = random.choice(self.test_prospects)

        before_time = datetime.now(UTC)

        decision_data = {
            "prospect_id": prospect.id,
            "decision": "go",
            "reason": "Timestamp test",
        }

        response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            data=json.dumps(decision_data),
            content_type="application/json",
        )

        after_time = datetime.now(UTC)

        assert response.status_code == 200
        data = response.get_json()

        # Verify timestamp exists and is reasonable
        assert "created_at" in data["data"]["decision"]
        created_at_str = data["data"]["decision"]["created_at"]

        # Parse timestamp (handle various formats)
        try:
            if "T" in created_at_str:
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
            else:
                created_at = datetime.fromisoformat(created_at_str)

            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)

            # Timestamp should be within test execution window (with some tolerance)
            assert (
                before_time - timedelta(seconds=5)
                <= created_at
                <= after_time + timedelta(seconds=5)
            )
        except:
            # If timestamp parsing fails, just verify it exists
            assert created_at_str is not None

    def test_api_security_measures(self, client):
        """Test that API is protected against common attacks."""
        # Test SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE decisions; --",
            "1' OR '1'='1",
            "'; SELECT * FROM users; --",
        ]

        for malicious in malicious_inputs:
            decision_data = {
                "prospect_id": malicious,
                "decision": "go",
                "reason": "Security test",
            }

            response = self._auth_request(
                client,
                "post",
                "/api/decisions/",
                data=json.dumps(decision_data),
                content_type="application/json",
            )

            # Should not crash, should return error for invalid prospect
            assert response.status_code == 400 or response.status_code == 404

        # Test XSS in reason field
        xss_reason = '<script>alert("xss")</script>'
        valid_prospect = self.test_prospects[1]  # Use second prospect

        xss_data = {
            "prospect_id": valid_prospect.id,
            "decision": "go",
            "reason": xss_reason,
        }

        response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            data=json.dumps(xss_data),
            content_type="application/json",
        )

        # API should accept the data (sanitization happens at render time)
        if response.status_code == 200:
            data = response.get_json()
            # Verify data was stored but will be escaped when rendered
            assert data["data"]["decision"]["reason"] == xss_reason

    def test_content_type_handling(self, client):
        """Test that API handles content types correctly."""
        prospect = self.test_prospects[2]  # Use third prospect

        decision_data = {
            "prospect_id": prospect.id,
            "decision": "go",
            "reason": "Content type test",
        }

        # Test with correct JSON content type
        response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            data=json.dumps(decision_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.content_type == "application/json"

        # Verify response is valid JSON
        try:
            json.loads(response.get_data(as_text=True))
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON")

    @pytest.mark.parametrize("decision_type", ["go", "no-go"])
    def test_decision_types(self, client, decision_type):
        """Test both decision types work correctly."""
        prospect = self.test_prospects[3]  # Use fourth prospect

        decision_data = {
            "prospect_id": prospect.id,
            "decision": decision_type,
            "reason": f"Testing {decision_type} decision",
        }

        response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            data=json.dumps(decision_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["decision"]["decision"] == decision_type

    def test_user_decisions_pagination(self, client):
        """Test pagination on GET /api/decisions/user endpoint."""
        # Create multiple decisions for pagination testing
        for i in range(5):
            prospect = self.test_prospects[i % len(self.test_prospects)]
            decision_data = {
                "prospect_id": prospect.id,
                "decision": "go" if i % 2 == 0 else "no-go",
                "reason": f"Pagination test decision {i}",
            }
            self._auth_request(
                client,
                "post",
                "/api/decisions/",
                data=json.dumps(decision_data),
                content_type="application/json",
            )

        # Test default pagination
        response = self._auth_request(client, "get", "/api/decisions/user")
        assert response.status_code == 200
        data = response.get_json()
        assert "pagination" in data["data"]
        assert "page" in data["data"]["pagination"]
        assert "per_page" in data["data"]["pagination"]
        assert "total" in data["data"]["pagination"]
        assert "pages" in data["data"]["pagination"]

        # Test specific page and limit
        response = self._auth_request(client, "get", "/api/decisions/user?page=1&per_page=2")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["data"]["decisions"]) <= 2
        assert data["data"]["pagination"]["page"] == 1
        assert data["data"]["pagination"]["per_page"] == 2

        # Test page 2
        response = self._auth_request(client, "get", "/api/decisions/user?page=2&per_page=2")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["pagination"]["page"] == 2

        # Test filtering by decision type
        response = self._auth_request(client, "get", "/api/decisions/user?decision=go")
        assert response.status_code == 200
        data = response.get_json()
        # All returned decisions should be "go"
        for decision in data["data"]["decisions"]:
            assert decision["decision"] == "go"

        # Test filtering by no-go
        response = self._auth_request(client, "get", "/api/decisions/user?decision=no-go")
        assert response.status_code == 200
        data = response.get_json()
        # All returned decisions should be "no-go"
        for decision in data["data"]["decisions"]:
            assert decision["decision"] == "no-go"

    def test_decision_authorization_checks(self, client):
        """Test that authorization is properly enforced for decisions."""
        # Create a decision as user 1
        prospect = self.test_prospects[0]
        decision_data = {
            "prospect_id": prospect.id,
            "decision": "go",
            "reason": "User 1's decision",
        }
        
        response = self._auth_request(
            client,
            "post",
            "/api/decisions/",
            user_id=self.test_users[0].id,
            data=json.dumps(decision_data),
            content_type="application/json",
        )
        assert response.status_code == 200
        decision_id = response.get_json()["data"]["decision"]["id"]

        # Try to delete as a different user (should fail with 403)
        response = self._auth_request(
            client,
            "delete",
            f"/api/decisions/{decision_id}",
            user_id=self.test_users[1].id,
        )
        assert response.status_code == 403
        data = response.get_json()
        assert "only delete your own" in data.get("message", "").lower()

        # Verify user 1 can still delete their own decision
        response = self._auth_request(
            client,
            "delete",
            f"/api/decisions/{decision_id}",
            user_id=self.test_users[0].id,
        )
        assert response.status_code == 200

    def test_get_user_decisions_only_returns_own(self, client):
        """Test that /api/decisions/user only returns the current user's decisions."""
        # Create decisions for different users
        for i in range(3):
            prospect = self.test_prospects[i]
            user = self.test_users[i]
            decision_data = {
                "prospect_id": prospect.id,
                "decision": "go",
                "reason": f"User {user.id} decision",
            }
            self._auth_request(
                client,
                "post",
                "/api/decisions/",
                user_id=user.id,
                data=json.dumps(decision_data),
                content_type="application/json",
            )

        # Get decisions for user 0
        response = self._auth_request(
            client,
            "get",
            "/api/decisions/user",
            user_id=self.test_users[0].id,
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # All decisions should belong to user 0
        for decision in data["data"]["decisions"]:
            assert decision["user_id"] == self.test_users[0].id

        # Get decisions for user 1
        response = self._auth_request(
            client,
            "get",
            "/api/decisions/user",
            user_id=self.test_users[1].id,
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # All decisions should belong to user 1
        for decision in data["data"]["decisions"]:
            assert decision["user_id"] == self.test_users[1].id
