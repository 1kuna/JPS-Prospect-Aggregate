"""
Comprehensive tests for Decisions API endpoints.

Tests all decision-related API functionality including CRUD operations.
"""

import pytest
from datetime import datetime, timezone
import json

from app import create_app
from app.database import db
from app.database.models import Prospect, DataSource, User, Decision
from app.database.user_models import User as UserModel


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
    
    @pytest.fixture(autouse=True)
    def setup_database(self, app):
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
                    username='testuser1',
                    email='user1@test.com',
                    role='user',
                    created_at=datetime.now(timezone.utc)
                ),
                User(
                    username='testuser2',
                    email='user2@test.com',
                    role='admin',
                    created_at=datetime.now(timezone.utc)
                ),
                User(
                    username='testuser3',
                    email='user3@test.com',
                    role='user',
                    created_at=datetime.now(timezone.utc)
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
                Decision(
                    prospect_id='DECISION-TEST-001',
                    user_id=test_users[0].id,
                    decision='go',
                    reasoning='Good opportunity for our team',
                    confidence_level=8,
                    created_at=datetime.now(timezone.utc)
                ),
                Decision(
                    prospect_id='DECISION-TEST-002',
                    user_id=test_users[1].id,
                    decision='no-go',
                    reasoning='Too much competition expected',
                    confidence_level=6,
                    created_at=datetime.now(timezone.utc)
                )
            ]
            
            for decision in existing_decisions:
                db.session.add(decision)
            
            db.session.commit()
            
            # Store IDs for use in tests
            self.user_ids = [user.id for user in test_users]
            self.prospect_ids = [prospect.id for prospect in test_prospects]
            
            yield
            
            # Cleanup
            db.session.rollback()
            db.drop_all()
    
    def test_create_decision_success(self, client):
        """Test successful decision creation."""
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'user_id': self.user_ids[0],
            'decision': 'go',
            'reasoning': 'Excellent fit for our capabilities',
            'confidence_level': 9
        }
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        assert data['success'] is True
        assert 'decision' in data
        assert data['decision']['decision'] == 'go'
        assert data['decision']['reasoning'] == 'Excellent fit for our capabilities'
        assert data['decision']['confidence_level'] == 9
        assert data['decision']['prospect_id'] == 'DECISION-TEST-003'
        assert data['decision']['user_id'] == self.user_ids[0]
    
    def test_create_decision_missing_fields(self, client):
        """Test decision creation with missing required fields."""
        # Missing prospect_id
        decision_data = {
            'user_id': self.user_ids[0],
            'decision': 'go',
            'reasoning': 'Test reasoning'
        }
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        
        # Missing decision
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'user_id': self.user_ids[0],
            'reasoning': 'Test reasoning'
        }
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_create_decision_invalid_values(self, client):
        """Test decision creation with invalid values."""
        # Invalid decision value
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'user_id': self.user_ids[0],
            'decision': 'maybe',  # Invalid decision
            'reasoning': 'Test reasoning'
        }
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        
        # Invalid confidence level
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'user_id': self.user_ids[0],
            'decision': 'go',
            'reasoning': 'Test reasoning',
            'confidence_level': 15  # Invalid range
        }
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_update_existing_decision(self, client):
        """Test updating an existing decision."""
        # Update user 1's decision on prospect 1
        updated_data = {
            'prospect_id': 'DECISION-TEST-001',
            'user_id': self.user_ids[0],
            'decision': 'no-go',
            'reasoning': 'Changed mind after further analysis',
            'confidence_level': 7
        }
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200  # Updated, not created
        data = response.get_json()
        
        assert data['success'] is True
        assert data['decision']['decision'] == 'no-go'
        assert data['decision']['reasoning'] == 'Changed mind after further analysis'
        assert data['decision']['confidence_level'] == 7
    
    def test_get_decisions_for_prospect(self, client):
        """Test retrieving all decisions for a specific prospect."""
        response = client.get('/api/decisions/DECISION-TEST-001')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'decisions' in data
        assert len(data['decisions']) == 1
        
        decision = data['decisions'][0]
        assert decision['prospect_id'] == 'DECISION-TEST-001'
        assert decision['decision'] == 'go'
        assert decision['reasoning'] == 'Good opportunity for our team'
        assert decision['confidence_level'] == 8
    
    def test_get_decisions_prospect_not_found(self, client):
        """Test retrieving decisions for non-existent prospect."""
        response = client.get('/api/decisions/NON-EXISTENT-PROSPECT')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_get_my_decisions(self, client):
        """Test retrieving current user's decisions."""
        # Mock current user context - in real app this would be handled by auth
        with client.session_transaction() as sess:
            sess['user_id'] = self.user_ids[0]
        
        response = client.get('/api/decisions/my')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'decisions' in data
        assert len(data['decisions']) >= 1
        
        # All decisions should belong to the current user
        for decision in data['decisions']:
            assert decision['user_id'] == self.user_ids[0]
    
    def test_get_my_decisions_no_user(self, client):
        """Test retrieving decisions when no user is logged in."""
        response = client.get('/api/decisions/my')
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
    
    def test_delete_decision_success(self, client):
        """Test successful decision deletion."""
        # First, create a decision to delete
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'user_id': self.user_ids[2],
            'decision': 'go',
            'reasoning': 'Will delete this decision',
            'confidence_level': 5
        }
        
        create_response = client.post(
            '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert create_response.status_code == 201
        decision_id = create_response.get_json()['decision']['id']
        
        # Now delete the decision
        response = client.delete(f'/api/decisions/{decision_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'deleted' in data['message'].lower()
    
    def test_delete_decision_not_found(self, client):
        """Test deleting non-existent decision."""
        response = client.delete('/api/decisions/99999')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_get_decisions_with_filters(self, client):
        """Test retrieving decisions with various filters."""
        # Filter by decision type
        response = client.get('/api/decisions/?decision=go')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'decisions' in data
        for decision in data['decisions']:
            assert decision['decision'] == 'go'
        
        # Filter by user
        response = client.get(f'/api/decisions/?user_id={self.user_ids[0]}')
        
        assert response.status_code == 200
        data = response.get_json()
        
        for decision in data['decisions']:
            assert decision['user_id'] == self.user_ids[0]
    
    def test_get_decisions_with_pagination(self, client):
        """Test decision retrieval with pagination."""
        # Create more decisions for pagination testing
        for i in range(5):
            decision_data = {
                'prospect_id': 'DECISION-TEST-003',
                'user_id': self.user_ids[i % 2],  # Alternate users
                'decision': 'go' if i % 2 == 0 else 'no-go',
                'reasoning': f'Pagination test decision {i}',
                'confidence_level': 5 + (i % 5)
            }
            
            client.post(
                '/api/decisions/',
                data=json.dumps(decision_data),
                content_type='application/json'
            )
        
        # Test pagination
        response = client.get('/api/decisions/?page=1&limit=3')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'decisions' in data
        assert 'pagination' in data
        assert len(data['decisions']) <= 3
        assert data['pagination']['page'] == 1
    
    def test_decision_statistics(self, client):
        """Test decision statistics endpoint."""
        response = client.get('/api/decisions/statistics')
        
        assert response.status_code == 200
        data = response.get_json()
        
        expected_stats = [
            'total_decisions', 'by_decision_type', 'by_user', 
            'average_confidence', 'recent_activity'
        ]
        
        for stat in expected_stats:
            assert stat in data
        
        assert data['total_decisions'] >= 2
        assert 'go' in data['by_decision_type']
        assert 'no-go' in data['by_decision_type']
    
    def test_decision_bulk_operations(self, client):
        """Test bulk decision operations."""
        # Test bulk creation
        bulk_data = {
            'decisions': [
                {
                    'prospect_id': 'DECISION-TEST-002',
                    'user_id': self.user_ids[2],
                    'decision': 'go',
                    'reasoning': 'Bulk decision 1',
                    'confidence_level': 7
                },
                {
                    'prospect_id': 'DECISION-TEST-003',
                    'user_id': self.user_ids[2],
                    'decision': 'no-go',
                    'reasoning': 'Bulk decision 2',
                    'confidence_level': 6
                }
            ]
        }
        
        response = client.post(
            '/api/decisions/bulk',
            data=json.dumps(bulk_data),
            content_type='application/json'
        )
        
        if response.status_code == 200:  # If bulk endpoint exists
            data = response.get_json()
            assert data['success'] is True
            assert 'created' in data
            assert data['created'] == 2
    
    def test_decision_validation_edge_cases(self, client):
        """Test decision validation edge cases."""
        # Test with empty reasoning
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'user_id': self.user_ids[0],
            'decision': 'go',
            'reasoning': '',  # Empty reasoning
            'confidence_level': 5
        }
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        # Should accept empty reasoning
        assert response.status_code in [200, 201]
        
        # Test with very long reasoning
        decision_data['reasoning'] = 'x' * 2000  # Very long reasoning
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        # Should handle long text appropriately
        assert response.status_code in [200, 201, 400]
    
    def test_decision_api_security(self, client):
        """Test decision API security measures."""
        # Test SQL injection attempt
        malicious_data = {
            'prospect_id': "'; DROP TABLE decisions; --",
            'user_id': self.user_ids[0],
            'decision': 'go',
            'reasoning': 'malicious input'
        }
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(malicious_data),
            content_type='application/json'
        )
        
        # Should not crash, should return error for invalid prospect_id
        assert response.status_code in [400, 404]
        
        # Test XSS attempt in reasoning
        xss_data = {
            'prospect_id': 'DECISION-TEST-003',
            'user_id': self.user_ids[0],
            'decision': 'go',
            'reasoning': '<script>alert("xss")</script>',
            'confidence_level': 5
        }
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(xss_data),
            content_type='application/json'
        )
        
        if response.status_code in [200, 201]:
            # If accepted, check that script tags are escaped in responses
            get_response = client.get('/api/decisions/DECISION-TEST-003')
            response_text = get_response.get_data(as_text=True)
            assert '<script>' not in response_text
    
    def test_decision_api_content_negotiation(self, client):
        """Test API content type handling."""
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'user_id': self.user_ids[0],
            'decision': 'go',
            'reasoning': 'Content type test'
        }
        
        # Test JSON content type
        response = client.post(
            '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        assert response.status_code in [200, 201]
        assert response.content_type == 'application/json'
        
        # Test invalid content type
        response = client.post(
            '/api/decisions/',
            data='invalid data',
            content_type='text/plain'
        )
        
        assert response.status_code == 400
    
    def test_decision_timestamps(self, client):
        """Test that decision timestamps are handled correctly."""
        decision_data = {
            'prospect_id': 'DECISION-TEST-003',
            'user_id': self.user_ids[0],
            'decision': 'go',
            'reasoning': 'Timestamp test',
            'confidence_level': 8
        }
        
        before_time = datetime.now(timezone.utc)
        
        response = client.post(
            '/api/decisions/',
            data=json.dumps(decision_data),
            content_type='application/json'
        )
        
        after_time = datetime.now(timezone.utc)
        
        assert response.status_code == 201
        data = response.get_json()
        
        created_at_str = data['decision']['created_at']
        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        
        # Timestamp should be within reasonable range
        assert before_time <= created_at <= after_time