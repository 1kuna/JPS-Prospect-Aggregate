"""
Integration tests for API workflows covering user journeys and cross-layer interactions.
These tests use a real database and test complete workflows from API to database.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from app import create_app
from app.database import db
from app.database.models import Prospect, DataSource
from app.database.operations import add_prospect


@pytest.fixture(scope="function")
def app():
    """Create a test Flask application with in-memory database."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    # Create app with test configuration
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ['USER_DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ['TESTING'] = 'True'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create a test data source
        test_source = DataSource(
            name='Test Agency',
            url='https://test.gov', 
            scraper_class='TestScraper',
            active=True
        )
        db.session.add(test_source)
        db.session.commit()
        
        # Store ID for tests
        app.config['TEST_SOURCE_ID'] = test_source.id
        app.config['TEST_USER_ID'] = 'test-user-123'
        
        yield app
        
        db.session.remove()
        db.drop_all()
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    """Create an authenticated test client."""
    # Mock authentication for testing
    with patch('app.api.auth.get_current_user') as mock_auth:
        mock_auth.return_value = {
            'id': app.config['TEST_USER_ID'],
            'username': 'testuser',
            'role': 'user'
        }
        yield client


class TestProspectWorkflow:
    """Test complete prospect management workflows."""
    
    def test_prospect_creation_and_retrieval_workflow(self, app, client):
        """Test creating prospects and retrieving them through the API."""
        with app.app_context():
            # Create test prospects directly using SQLAlchemy models
            test_prospect_1 = Prospect(
                id='TEST-001',
                title='Software Development Services',
                description='Custom software development for government',
                agency='Department of Defense',
                posted_date=datetime(2024, 1, 15).date(),
                estimated_value=100000,
                estimated_value_text='$100,000',
                naics='541511',
                source_data_id=app.config['TEST_SOURCE_ID'],
                source_file='test_data.json',
                loaded_at=datetime.now(timezone.utc)
            )
            
            test_prospect_2 = Prospect(
                id='TEST-002',
                title='Cloud Infrastructure Setup',
                description='Cloud migration and setup services',
                agency='Health and Human Services',
                posted_date=datetime(2024, 1, 16).date(),
                estimated_value=75000,
                estimated_value_text='$75,000',
                naics='518210',
                source_data_id=app.config['TEST_SOURCE_ID'],
                source_file='test_data.json',
                loaded_at=datetime.now(timezone.utc)
            )
            
            # Add prospects to database
            db.session.add(test_prospect_1)
            db.session.add(test_prospect_2)
            db.session.commit()
        
        # Test API retrieval - basic pagination
        response = client.get('/api/prospects')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'prospects' in data
        assert 'pagination' in data
        assert len(data['prospects']) == 2
        assert data['pagination']['total_items'] == 2
        
        # Verify prospect data structure
        prospect = data['prospects'][0]
        required_fields = ['id', 'title', 'description', 'agency', 'posted_date', 
                          'estimated_value', 'naics', 'loaded_at']
        for field in required_fields:
            assert field in prospect
    
    def test_prospect_filtering_workflow(self, app, client):
        """Test prospect filtering through API with various filter combinations."""
        with app.app_context():
            # Create diverse test data
            prospects_data = [
                {
                    'id': 'FILTER-001',
                    'title': 'Python Development Services',
                    'description': 'Python web application development',
                    'agency': 'Department of Defense',
                    'naics_code': '541511',
                    'estimated_value': 50000,
                    'source_data_id': app.config['TEST_SOURCE_ID'],
                    'ai_enhanced_title': 'Enhanced: Python Development Services',
                    'ollama_processed_at': datetime.now(timezone.utc)
                },
                {
                    'id': 'FILTER-002', 
                    'title': 'Java Application Development',
                    'description': 'Enterprise Java application development',
                    'agency': 'Department of Commerce',
                    'naics_code': '541511',
                    'estimated_value': 125000,
                    'source_data_id': app.config['TEST_SOURCE_ID']
                },
                {
                    'id': 'FILTER-003',
                    'title': 'Network Security Services',
                    'description': 'Cybersecurity and network protection',
                    'agency': 'Department of Defense',
                    'naics_code': '541512',
                    'estimated_value': 200000,
                    'source_data_id': app.config['TEST_SOURCE_ID']
                }
            ]
            
            for prospect_data in prospects_data:
                prospect_data.update({
                    'posted_date': '2024-01-15',
                    'estimated_value_text': f"${prospect_data['estimated_value']:,}",
                    'source_file': 'filter_test.json',
                    'loaded_at': datetime.now(timezone.utc)
                })
                add_prospect(prospect_data)
        
        # Test NAICS code filtering
        response = client.get('/api/prospects?naics=541511')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['prospects']) == 2
        for prospect in data['prospects']:
            assert prospect['naics_code'] == '541511'
        
        # Test agency filtering
        response = client.get('/api/prospects?agency=Department of Defense')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['prospects']) == 2
        for prospect in data['prospects']:
            assert prospect['agency'] == 'Department of Defense'
        
        # Test keyword search
        response = client.get('/api/prospects?keywords=Python')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['prospects']) == 1
        assert 'Python' in data['prospects'][0]['title']
        
        # Test AI enhancement filtering
        response = client.get('/api/prospects?ai_enrichment=enhanced')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['prospects']) == 1
        assert data['prospects'][0]['ai_enhanced_title'] is not None
        
        # Test combined filters
        response = client.get('/api/prospects?naics=541511&agency=Department of Defense')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['prospects']) == 1
        assert data['prospects'][0]['id'] == 'FILTER-001'
    
    def test_prospect_pagination_workflow(self, app, client):
        """Test prospect pagination with various page sizes and navigation."""
        with app.app_context():
            # Create 25 test prospects for pagination testing
            for i in range(25):
                prospect_data = {
                    'id': f'PAGE-{i:03d}',
                    'title': f'Test Prospect {i}',
                    'description': f'Description for prospect {i}',
                    'agency': 'Test Agency',
                    'posted_date': '2024-01-15',
                    'estimated_value': 10000 * (i + 1),
                    'estimated_value_text': f'${10000 * (i + 1):,}',
                    'naics_code': '541511',
                    'source_data_id': app.config['TEST_SOURCE_ID'],
                    'source_file': 'pagination_test.json',
                    'loaded_at': datetime.now(timezone.utc)
                }
                add_prospect(prospect_data)
        
        # Test default pagination (page 1, limit 10)
        response = client.get('/api/prospects')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['prospects']) == 10
        assert data['pagination']['page'] == 1
        assert data['pagination']['total_items'] == 25
        assert data['pagination']['total_pages'] == 3
        assert data['pagination']['has_next'] is True
        assert data['pagination']['has_prev'] is False
        
        # Test page 2
        response = client.get('/api/prospects?page=2')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['prospects']) == 10
        assert data['pagination']['page'] == 2
        assert data['pagination']['has_next'] is True
        assert data['pagination']['has_prev'] is True
        
        # Test last page
        response = client.get('/api/prospects?page=3')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['prospects']) == 5  # Remaining items
        assert data['pagination']['page'] == 3
        assert data['pagination']['has_next'] is False
        assert data['pagination']['has_prev'] is True
        
        # Test custom page size
        response = client.get('/api/prospects?limit=5')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['prospects']) == 5
        assert data['pagination']['total_pages'] == 5
        
        # Test out of range page
        response = client.get('/api/prospects?page=999')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['prospects']) == 0


class TestDecisionWorkflow:
    """Test complete decision management workflows."""
    
    def test_decision_creation_and_retrieval_workflow(self, app, auth_client):
        """Test creating and retrieving decisions through the API."""
        with app.app_context():
            # Create a test prospect for decisions
            prospect_data = {
                'id': 'DECISION-PROSPECT-001',
                'title': 'Decision Test Prospect',
                'description': 'A prospect for testing decisions',
                'agency': 'Test Agency',
                'posted_date': '2024-01-15',
                'estimated_value': 50000,
                'estimated_value_text': '$50,000',
                'naics_code': '541511',
                'source_data_id': app.config['TEST_SOURCE_ID'],
                'source_file': 'decision_test.json',
                'loaded_at': datetime.now(timezone.utc)
            }
            add_prospect(prospect_data)
        
        # Create a Go decision
        decision_data = {
            'prospect_id': 'DECISION-PROSPECT-001',
            'decision': 'go',
            'reason': 'Good fit for our services and capabilities'
        }
        
        response = auth_client.post('/api/decisions/', 
                                  data=json.dumps(decision_data),
                                  content_type='application/json')
        assert response.status_code == 201
        
        created_decision = response.get_json()
        assert created_decision['data']['decision']['decision'] == 'go'
        assert created_decision['data']['decision']['prospect_id'] == 'DECISION-PROSPECT-001'
        decision_id = created_decision['data']['decision']['id']
        
        # Retrieve decisions for the prospect
        response = auth_client.get(f'/api/decisions/DECISION-PROSPECT-001')
        assert response.status_code == 200
        
        decisions_data = response.get_json()
        assert decisions_data['data']['total_decisions'] == 1
        assert len(decisions_data['data']['decisions']) == 1
        assert decisions_data['data']['decisions'][0]['decision'] == 'go'
        
        # Test updating decision to no-go
        update_data = {
            'prospect_id': 'DECISION-PROSPECT-001',
            'decision': 'no-go',
            'reason': 'Changed priorities, not a good fit anymore'
        }
        
        response = auth_client.post('/api/decisions/',
                                  data=json.dumps(update_data),
                                  content_type='application/json')
        assert response.status_code == 201
        
        # Should now have 2 decisions (history is kept)
        response = auth_client.get(f'/api/decisions/DECISION-PROSPECT-001')
        assert response.status_code == 200
        decisions_data = response.get_json()
        assert decisions_data['data']['total_decisions'] == 2
        
        # Most recent should be no-go
        latest_decision = max(decisions_data['data']['decisions'], 
                            key=lambda d: d['created_at'])
        assert latest_decision['decision'] == 'no-go'
    
    def test_decision_stats_workflow(self, app, auth_client):
        """Test decision statistics aggregation."""
        with app.app_context():
            # Create multiple prospects and decisions
            prospects_and_decisions = [
                ('STATS-001', 'go', 'Good opportunity'),
                ('STATS-002', 'go', 'Excellent fit'),
                ('STATS-003', 'no-go', 'Not aligned with strategy'),
                ('STATS-004', 'go', 'Strong potential'),
                ('STATS-005', 'no-go', 'Too much risk')
            ]
            
            for prospect_id, decision, reason in prospects_and_decisions:
                # Create prospect
                prospect_data = {
                    'id': prospect_id,
                    'title': f'Stats Test Prospect {prospect_id}',
                    'description': f'Description for {prospect_id}',
                    'agency': 'Stats Test Agency',
                    'posted_date': '2024-01-15',
                    'estimated_value': 50000,
                    'estimated_value_text': '$50,000',
                    'naics_code': '541511',
                    'source_data_id': app.config['TEST_SOURCE_ID'],
                    'source_file': 'stats_test.json',
                    'loaded_at': datetime.now(timezone.utc)
                }
                add_prospect(prospect_data)
                
                # Create decision
                decision_data = {
                    'prospect_id': prospect_id,
                    'decision': decision,
                    'reason': reason
                }
                
                response = auth_client.post('/api/decisions/',
                                          data=json.dumps(decision_data),
                                          content_type='application/json')
                assert response.status_code == 201
        
        # Get decision statistics
        response = auth_client.get('/api/decisions/stats')
        assert response.status_code == 200
        
        stats = response.get_json()['data']
        assert stats['total_decisions'] == 5
        assert stats['go_decisions'] == 3
        assert stats['no_go_decisions'] == 2
        assert len(stats['decisions_by_user']) >= 1
        assert len(stats['recent_decisions']) >= 1
        
        # Verify user has correct decision count
        user_stats = next(u for u in stats['decisions_by_user'] 
                         if u['username'] == 'testuser')
        assert user_stats['decision_count'] == 5


class TestDataSourceWorkflow:
    """Test data source management workflows."""
    
    def test_data_source_listing_workflow(self, app, client):
        """Test retrieving data sources through the API."""
        response = client.get('/api/data-sources')
        assert response.status_code == 200
        
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1  # Should have the test source
        
        # Verify data source structure
        source = data[0]
        required_fields = ['id', 'name', 'url', 'scraper_class', 'active', 'last_scraped']
        for field in required_fields:
            assert field in source
        
        assert source['name'] == 'Test Agency'
        assert source['active'] is True


class TestHealthWorkflow:
    """Test application health and status workflows."""
    
    def test_health_check_workflow(self, app, client):
        """Test health check endpoints."""
        response = client.get('/api/health')
        assert response.status_code == 200
        
        health_data = response.get_json()
        assert 'status' in health_data
        assert 'database' in health_data
        assert 'timestamp' in health_data
        
        assert health_data['status'] == 'healthy'
        assert health_data['database'] == 'connected'
    
    def test_database_status_workflow(self, app, client):
        """Test database connectivity verification."""
        response = client.get('/api/health/database')
        assert response.status_code == 200
        
        db_health = response.get_json()
        assert 'status' in db_health
        assert 'connection' in db_health
        assert 'prospect_count' in db_health
        
        assert db_health['status'] == 'healthy'
        assert db_health['connection'] == 'ok'
        assert isinstance(db_health['prospect_count'], int)


class TestErrorHandlingWorkflow:
    """Test error handling across API endpoints."""
    
    def test_prospect_not_found_workflow(self, app, client):
        """Test handling of non-existent prospect requests."""
        response = client.get('/api/prospects/NON-EXISTENT-ID')
        assert response.status_code == 404
        
        error_data = response.get_json()
        assert 'error' in error_data
        assert 'message' in error_data
    
    def test_invalid_pagination_workflow(self, app, client):
        """Test handling of invalid pagination parameters."""
        # Test negative page
        response = client.get('/api/prospects?page=-1')
        assert response.status_code == 400
        
        # Test invalid limit
        response = client.get('/api/prospects?limit=0')
        assert response.status_code == 400
        
        # Test excessive limit
        response = client.get('/api/prospects?limit=1000')
        assert response.status_code == 400
    
    def test_malformed_decision_workflow(self, app, auth_client):
        """Test handling of malformed decision requests."""
        # Missing required fields
        response = auth_client.post('/api/decisions/',
                                  data=json.dumps({}),
                                  content_type='application/json')
        assert response.status_code == 400
        
        # Invalid decision type
        invalid_decision = {
            'prospect_id': 'TEST-001',
            'decision': 'invalid-decision',
            'reason': 'Test reason'
        }
        
        response = auth_client.post('/api/decisions/',
                                  data=json.dumps(invalid_decision),
                                  content_type='application/json')
        assert response.status_code == 400


class TestConcurrencyWorkflow:
    """Test concurrent operations and data consistency."""
    
    def test_concurrent_decision_creation_workflow(self, app, auth_client):
        """Test handling of concurrent decision creation for same prospect."""
        with app.app_context():
            # Create test prospect
            prospect_data = {
                'id': 'CONCURRENT-001',
                'title': 'Concurrent Test Prospect',
                'description': 'Testing concurrent operations',
                'agency': 'Test Agency',
                'posted_date': '2024-01-15',
                'estimated_value': 50000,
                'estimated_value_text': '$50,000',
                'naics_code': '541511',
                'source_data_id': app.config['TEST_SOURCE_ID'],
                'source_file': 'concurrent_test.json',
                'loaded_at': datetime.now(timezone.utc)
            }
            add_prospect(prospect_data)
        
        # Create multiple decisions rapidly
        decisions = [
            {'prospect_id': 'CONCURRENT-001', 'decision': 'go', 'reason': 'First decision'},
            {'prospect_id': 'CONCURRENT-001', 'decision': 'no-go', 'reason': 'Second decision'},
            {'prospect_id': 'CONCURRENT-001', 'decision': 'go', 'reason': 'Third decision'}
        ]
        
        responses = []
        for decision_data in decisions:
            response = auth_client.post('/api/decisions/',
                                      data=json.dumps(decision_data),
                                      content_type='application/json')
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 201
        
        # Verify all decisions were recorded
        response = auth_client.get('/api/decisions/CONCURRENT-001')
        assert response.status_code == 200
        
        decisions_data = response.get_json()
        assert decisions_data['data']['total_decisions'] == 3


if __name__ == '__main__':
    pytest.main([__file__])