"""
Integration tests for LLM processing API endpoints.

Tests real API interactions with database but mocks external services.
"""

import pytest
from unittest.mock import patch, Mock
import json
from flask import url_for
from datetime import datetime, timezone

from app import create_app
from app.database import db
from app.database.models import Prospect, DataSource, User


@pytest.mark.integration
class TestLLMAPIIntegration:
    """Integration tests for LLM processing API."""
    
    @pytest.fixture(scope='class')
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
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
                name='Test Agency',
                url='https://test.gov',
                last_scraped=datetime.now(timezone.utc)
            )
            db.session.add(data_source)
            db.session.flush()
            
            # Create test user
            user = User(
                username='testuser',
                email='test@example.com',
                role='admin'
            )
            db.session.add(user)
            db.session.flush()
            
            # Create test prospects
            prospects = [
                Prospect(
                    title='AI Software Development',
                    agency='Test Agency',
                    description='Development of AI software solutions',
                    estimated_value_text='$100,000 - $500,000',
                    naics='541511',
                    posted_date=datetime.now(timezone.utc).date(),
                    response_date=datetime.now(timezone.utc).date(),
                    source_id=data_source.id,
                    notice_id='TEST-001'
                ),
                Prospect(
                    title='Cybersecurity Consulting',
                    agency='Test Agency',
                    description='Security assessment and consulting',
                    estimated_value_text='$50,000',
                    posted_date=datetime.now(timezone.utc).date(),
                    response_date=datetime.now(timezone.utc).date(),
                    source_id=data_source.id,
                    notice_id='TEST-002'
                ),
                Prospect(
                    title='Data Analytics Platform',
                    agency='Test Agency',
                    description='Big data analytics platform development',
                    estimated_value_text='TBD',
                    posted_date=datetime.now(timezone.utc).date(),
                    response_date=datetime.now(timezone.utc).date(),
                    source_id=data_source.id,
                    notice_id='TEST-003',
                    ollama_processed_at=datetime.now(timezone.utc),
                    estimated_value_single=200000,
                    title_enhanced='Enhanced Data Analytics Platform',
                    naics_source='llm_inferred'
                )
            ]
            
            for prospect in prospects:
                db.session.add(prospect)
            
            db.session.commit()
            
            yield
            
            # Cleanup
            db.session.rollback()
            db.drop_all()
    
    @patch('app.api.llm_processing.admin_required')
    def test_get_llm_status_integration(self, mock_admin, client, app):
        """Test LLM status endpoint with real database queries."""
        # Mock admin decorator
        mock_admin.side_effect = lambda f: f
        
        with patch('app.api.llm_processing.enhancement_queue') as mock_queue:
            mock_queue.get_queue_status.return_value = {
                'total_items': 2,
                'pending_items': 1,
                'processing_items': 1,
                'is_processing': True
            }
            
            with patch('app.api.llm_processing.llm_service') as mock_llm:
                mock_llm.check_ollama_status.return_value = {
                    'available': True,
                    'model': 'qwen3:latest'
                }
                
                response = client.get('/api/llm/status')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify database queries worked
        assert data['total_prospects'] == 3
        assert data['processed_prospects'] == 1  # Only one has ollama_processed_at
        assert data['processing_percentage'] == 33.33
        
        # Verify NAICS statistics
        assert data['naics_coverage']['original'] == 1  # One with naics but not llm_inferred
        assert data['naics_coverage']['llm_inferred'] == 1  # One with llm_inferred source
        
        # Verify value parsing statistics
        assert data['value_parsing']['parsed_count'] == 1  # Only one has estimated_value_single
        
        # Verify queue and LLM status
        assert data['queue_status']['total_items'] == 2
        assert data['llm_status']['available'] is True
    
    @patch('app.api.llm_processing.admin_required')
    @patch('app.api.llm_processing.add_individual_enhancement')
    def test_enhance_prospect_integration(self, mock_add, mock_admin, client):
        """Test adding prospect to enhancement queue."""
        # Mock admin decorator
        mock_admin.side_effect = lambda f: f
        
        # Mock enhancement function
        mock_add.return_value = {
            'success': True,
            'queue_position': 1,
            'message': 'Added to enhancement queue at position 1'
        }
        
        response = client.post(
            '/api/llm/enhance',
            json={
                'prospect_id': '1',
                'force_redo': True,
                'enhancement_types': ['values', 'titles']
            },
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['queue_position'] == 1
        
        # Verify the enhancement function was called with correct parameters
        mock_add.assert_called_once()
        call_kwargs = mock_add.call_args[1]
        assert call_kwargs['prospect_id'] == '1'
        assert call_kwargs['force_redo'] is True
        assert call_kwargs['enhancement_types'] == ['values', 'titles']
    
    @patch('app.api.llm_processing.admin_required')
    def test_enhance_prospect_missing_data(self, mock_admin, client):
        """Test enhancement request with missing prospect_id."""
        mock_admin.side_effect = lambda f: f
        
        response = client.post(
            '/api/llm/enhance',
            json={'force_redo': True},
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'prospect_id' in data['error']
    
    @patch('app.api.llm_processing.admin_required')
    @patch('app.api.llm_processing.enhancement_queue')
    def test_queue_status_integration(self, mock_queue, mock_admin, client):
        """Test queue status endpoint."""
        mock_admin.side_effect = lambda f: f
        mock_queue.get_queue_status.return_value = {
            'total_items': 5,
            'pending_items': 3,
            'processing_items': 1,
            'completed_items': 1,
            'is_processing': True,
            'current_item': '123'
        }
        
        response = client.get('/api/llm/queue/status')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total_items'] == 5
        assert data['is_processing'] is True
        assert data['current_item'] == '123'
    
    @patch('app.api.llm_processing.admin_required')
    @patch('app.api.llm_processing.enhancement_queue')
    def test_queue_item_status_integration(self, mock_queue, mock_admin, client):
        """Test individual queue item status."""
        mock_admin.side_effect = lambda f: f
        mock_queue.get_item_status.return_value = {
            'status': 'processing',
            'queue_position': 2,
            'enhancement_types': ['values', 'titles'],
            'progress': {
                'values': {'completed': True},
                'titles': {'completed': False}
            },
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        response = client.get('/api/llm/queue/item/123')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'processing'
        assert data['queue_position'] == 2
        assert data['progress']['values']['completed'] is True
    
    @patch('app.api.llm_processing.admin_required')
    @patch('app.api.llm_processing.enhancement_queue')
    def test_queue_item_not_found(self, mock_queue, mock_admin, client):
        """Test queue item status for non-existent item."""
        mock_admin.side_effect = lambda f: f
        mock_queue.get_item_status.return_value = None
        
        response = client.get('/api/llm/queue/item/999')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    @patch('app.api.llm_processing.admin_required')
    @patch('app.api.llm_processing.enhancement_queue')
    def test_remove_from_queue_integration(self, mock_queue, mock_admin, client):
        """Test removing item from queue."""
        mock_admin.side_effect = lambda f: f
        mock_queue.remove_from_queue.return_value = True
        
        response = client.delete('/api/llm/queue/item/123')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        mock_queue.remove_from_queue.assert_called_once_with('123')
    
    @patch('app.api.llm_processing.admin_required')
    @patch('app.api.llm_processing.enhancement_queue')
    def test_start_queue_processing_integration(self, mock_queue, mock_admin, client):
        """Test starting queue processing."""
        mock_admin.side_effect = lambda f: f
        
        response = client.post('/api/llm/queue/start')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'started' in data['message']
        
        mock_queue.start_processing.assert_called_once()
    
    @patch('app.api.llm_processing.admin_required')
    @patch('app.api.llm_processing.enhancement_queue')
    def test_stop_queue_processing_integration(self, mock_queue, mock_admin, client):
        """Test stopping queue processing."""
        mock_admin.side_effect = lambda f: f
        
        response = client.post('/api/llm/queue/stop')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'stopped' in data['message']
        
        mock_queue.stop_processing.assert_called_once()
    
    @patch('app.api.llm_processing.admin_required')
    @patch('app.api.llm_processing.enhancement_queue')
    def test_clear_completed_items_integration(self, mock_queue, mock_admin, client):
        """Test clearing completed queue items."""
        mock_admin.side_effect = lambda f: f
        mock_queue.clear_completed_items.return_value = 3
        
        response = client.post('/api/llm/queue/clear-completed')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['cleared_count'] == 3
    
    @patch('app.api.llm_processing.admin_required')
    def test_enhancement_history_integration(self, mock_admin, client, app):
        """Test enhancement history endpoint with database queries."""
        mock_admin.side_effect = lambda f: f
        
        # This would require actual AIEnrichmentLog entries
        # For now we test the endpoint structure
        response = client.get('/api/llm/history?limit=10&offset=0')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'total' in data
        assert 'items' in data
        assert isinstance(data['items'], list)
    
    def test_api_error_handling(self, client):
        """Test API error handling for unauthenticated requests."""
        # Test that admin_required decorator works
        response = client.get('/api/llm/status')
        
        # Should get 401 or 403 depending on admin_required implementation
        assert response.status_code in [401, 403]
    
    @patch('app.api.llm_processing.admin_required')
    def test_stream_progress_endpoint(self, mock_admin, client):
        """Test SSE progress streaming endpoint."""
        mock_admin.side_effect = lambda f: f
        
        with patch('app.api.llm_processing.enhancement_queue') as mock_queue:
            mock_queue.get_queue_status.return_value = {
                'total_items': 1,
                'processing_items': 1,
                'current_item': '123',
                'current_step': 'Processing values'
            }
            
            response = client.get('/api/llm/stream/progress')
            
            assert response.status_code == 200
            assert response.content_type == 'text/plain; charset=utf-8'
            
            # Read first chunk of SSE data
            data_chunk = next(response.response)
            assert b'data:' in data_chunk
            assert b'current_step' in data_chunk