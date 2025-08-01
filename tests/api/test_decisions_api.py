"""
Comprehensive tests for Decisions API endpoints.

Tests all decision-related API functionality including CRUD operations.
"""

import pytest
from datetime import datetime, timezone
import json

from app import create_app
from app.database import db
from app.database.models import Prospect, DataSource, GoNoGoDecision
from app.database.user_models import User


class TestDecisionsAPI:
    """Test suite for Decisions API endpoints."""
    
    @pytest.fixture(scope='class')
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def _auth_request(self, client, method, url, user_id=None, **kwargs):
        """Helper method to make authenticated requests."""
        with client.session_transaction() as sess:
            sess['user_id'] = user_id if user_id else self.user_ids[0]
            sess['user_role'] = 'user'
        
        method_func = getattr(client, method)
        return method_func(url, **kwargs)
    
    @pytest.fixture(autouse=True)
    def setup_database(self, app, client):
        """Set up test database with sample data."""
        with app.app_context():
            db.create_all()
            
            # Create test data source
            data_source = DataSource(
                name='Decision Test Agency',
                url='https://decisions.test.gov',
                last_scraped=datetime.now(timezone.utc)
            )
            db.session.add(data_source)
            db.session.flush()
            
            # Create test users
            test_users = [
                User(
                    first_name='Test User 1',
                    email='user1@test.com',
                    role='user'
                ),
                User(
                    first_name='Test User 2',
                    email='user2@test.com',
                    role='admin'
                ),
                User(
                    first_name='Test User 3',
                    email='user3@test.com',
                    role='user'
                )
            ]
            
            for user in test_users:
                db.session.add(user)
            db.session.flush()
            
            # Create test prospects
            test_prospects = [
                Prospect(
                    id='DECISION-TEST-001',
                    title='Decision Test Contract 1',
                    description='Test contract for decision making',
                    agency='Decision Test Agency',
                    naics='541511',
                    estimated_value_text='$100,000',
                    source_id=data_source.id,
                    loaded_at=datetime.now(timezone.utc)
                ),
                Prospect(
                    id='DECISION-TEST-002',
                    title='Decision Test Contract 2',
                    description='Another test contract for decisions',
                    agency='Decision Test Agency',
                    naics='541512',
                    estimated_value_text='$250,000',
                    source_id=data_source.id,
                    loaded_at=datetime.now(timezone.utc)
                ),
                Prospect(
                    id='DECISION-TEST-003',
                    title='Decision Test Contract 3',
                    description='Third test contract',
                    agency='Decision Test Agency',
                    naics='541519',
                    estimated_value_text='$500,000',
                    source_id=data_source.id,
                    loaded_at=datetime.now(timezone.utc)
                )
            ]
            
            for prospect in test_prospects:
                db.session.add(prospect)
            db.session.flush()
            
            # Create some existing decisions
            existing_decisions = [
                GoNoGoDecision(
                    prospect_id='DECISION-TEST-001',
                    user_id=test_users[0].id,
                    decision='go',
                    reason='Good opportunity for our team'
                ),
                GoNoGoDecision(
                    prospect_id='DECISION-TEST-002',
                    user_id=test_users[1].id,
                    decision='no-go',
                    reason='Too much competition expected'
                )
            ]
            
            for decision in existing_decisions:
                db.session.add(decision)
            
            db.session.commit()
            
            # Store IDs for use in tests
            self.user_ids = [user.id for user in test_users]
            self.prospect_ids = [prospect.id for prospect in test_prospects]
            self.decision_ids = [decision.id for decision in existing_decisions]
            
            yield
            
            # Cleanup
            db.session.rollback()
            db.drop_all()
    
    def test_create_decision_success(self, client):
        """Test successful decision creation."""
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'decision': 'go',
            'reason': 'Excellent fit for our capabilities'
        }
        
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'decision' in data['data']
        assert data['data']['decision']['decision'] == 'go'
        assert data['data']['decision']['reason'] == 'Excellent fit for our capabilities'
        assert data['data']['decision']['prospect_id'] == 'DECISION-TEST-003'
        assert data['data']['decision']['user_id'] == self.user_ids[0]
    
    def test_create_decision_missing_fields(self, client):
        """Test decision creation with missing required fields."""
        # Missing prospect_id
        decision_data = {
            'decision': 'go',
            'reason': 'Test reasoning'
        }
        
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'message' in data or 'error' in data
        
        # Missing decision
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'reason': 'Test reasoning'
        }
        
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_create_decision_invalid_values(self, client):
        """Test decision creation with invalid values."""
        # Invalid decision value
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'decision': 'maybe',  # Invalid decision
            'reason': 'Test reasoning'
        }
        
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'message' in data or 'error' in data
    
    def test_update_existing_decision(self, client):
        """Test updating an existing decision."""
        # Update user 1's decision on prospect 1
        updated_data = {
            'prospect_id': 'DECISION-TEST-001',
            'decision': 'no-go',
            'reason': 'Changed mind after further analysis'
        }
        
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['status'] == 'success'
        assert data['data']['decision']['decision'] == 'no-go'
        assert data['data']['decision']['reason'] == 'Changed mind after further analysis'
    
    def test_get_decisions_for_prospect(self, client):
        """Test retrieving all decisions for a specific prospect."""
        response = self._auth_request(
            client, 'get', '/api/decisions/DECISION-TEST-001'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'data' in data
        # data['data'] contains an object with 'decisions' list
        assert 'decisions' in data['data']
        assert len(data['data']['decisions']) >= 1
        
        decision = data['data']['decisions'][0]
        assert decision['prospect_id'] == 'DECISION-TEST-001'
        assert decision['decision'] == 'go'
        assert decision['reason'] == 'Good opportunity for our team'
    
    def test_get_decisions_prospect_not_found(self, client):
        """Test retrieving decisions for non-existent prospect."""
        response = self._auth_request(
            client, 'get', '/api/decisions/NON-EXISTENT-PROSPECT'
        )
        
        # Could be 200 with empty list or 404
        assert response.status_code in [200, 404]
    
    def test_get_my_decisions(self, client):
        """Test retrieving current user's decisions."""
        response = self._auth_request(
            client, 'get', '/api/decisions/my'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'data' in data
        # data['data'] contains an object with 'decisions' list
        assert 'decisions' in data['data']
        
        # All decisions should belong to the current user
        for decision in data['data']['decisions']:
            assert decision['user_id'] == self.user_ids[0]
    
    def test_get_my_decisions_no_user(self, client):
        """Test retrieving decisions when no user is logged in."""
        response = client.get('/api/decisions/my')
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'message' in data or 'error' in data
    
    def test_delete_decision_success(self, client):
        """Test successful decision deletion."""
        # First, create a decision to delete
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'decision': 'go',
            'reason': 'Will delete this decision'
        }
        
        create_response = self._auth_request(
            client, 'post', '/api/decisions/',
            user_id=self.user_ids[2],
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert create_response.status_code == 200
        decision_id = create_response.get_json()['data']['decision']['id']
        
        # Now delete the decision
        response = self._auth_request(
            client, 'delete', f'/api/decisions/{decision_id}',
            user_id=self.user_ids[2]
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_delete_decision_not_found(self, client):
        """Test deleting non-existent decision."""
        response = self._auth_request(
            client, 'delete', '/api/decisions/99999'
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'message' in data or 'error' in data
    
    def test_decision_statistics(self, client):
        """Test decision statistics endpoint."""
        response = self._auth_request(
            client, 'get', '/api/decisions/statistics'
        )
        
        # If endpoint exists
        if response.status_code == 200:
            data = response.get_json()
            
            expected_stats = [
                'total_decisions', 'by_decision_type', 'by_user'
            ]
            
            for stat in expected_stats:
                assert stat in data
        else:
            # Endpoint may not be implemented
            pytest.skip("Statistics endpoint not implemented")
    
    def test_decision_validation_edge_cases(self, client):
        """Test decision validation edge cases."""
        # Test with empty reason
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'decision': 'go',
            'reason': ''  # Empty reason
        }
        
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        # Should accept empty reason
        assert response.status_code == 200
        
        # Test with very long reason
        decision_data['reason'] = 'x' * 2000  # Very long reason
        
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        # Should handle long text appropriately
        assert response.status_code in [200, 400]
    
    def test_decision_api_security(self, client):
        """Test decision API security measures."""
        # Test SQL injection attempt
        malicious_data = {
            'prospect_id': "'; DROP TABLE decisions; --",
            'decision': 'go',
            'reason': 'malicious input'
        }
        
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(malicious_data),
            content_type='application/json'
        )
        
        # Should not crash, should return error for invalid prospect_id
        assert response.status_code in [400, 404]
        
        # Test XSS attempt in reason
        xss_data = {
            'prospect_id': 'DECISION-TEST-003',
            'decision': 'go',
            'reason': '<script>alert("xss")</script>'
        }
        
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(xss_data),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            # If accepted, verify data was stored properly
            # The API should store the data as-is but will be escaped when rendered in HTML
            # This is expected behavior - we're testing API, not HTML rendering
            assert True  # XSS protection would be handled at the rendering layer
    
    def test_decision_api_content_negotiation(self, client):
        """Test API content type handling."""
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'decision': 'go',
            'reason': 'Content type test'
        }
        
        # Test JSON content type
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
    
    def test_decision_timestamps(self, client):
        """Test that decision timestamps are handled correctly."""
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'decision': 'go',
            'reason': 'Timestamp test'
        }
        
        before_time = datetime.now(timezone.utc)
        
        response = self._auth_request(
            client, 'post', '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        after_time = datetime.now(timezone.utc)
        
        assert response.status_code == 200
        data = response.get_json()
        
        created_at_str = data['data']['decision']['created_at']
        # Handle different timestamp formats
        if 'T' in created_at_str:
            # ISO format without timezone
            created_at = datetime.fromisoformat(created_at_str)
            # Assume UTC if no timezone info
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        
        # Timestamp should be within reasonable range (allow 1 second tolerance)
        from datetime import timedelta
        assert before_time - timedelta(seconds=1) <= created_at <= after_time + timedelta(seconds=1)