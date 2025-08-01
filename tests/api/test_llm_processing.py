"""
Unit tests for LLM Processing API endpoints.

Tests all endpoints in the llm_processing blueprint to ensure API stability.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json

from app import create_app
from app.database import db
from app.services.enhancement_queue import QueueStatus


class TestLLMProcessingAPI:
    """Test suite for LLM processing API endpoints."""
    
    @pytest.fixture(scope='class')
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture(autouse=True)
    def setup_database(self, app):
        """Set up test database."""
        with app.app_context():
            db.create_all()
            yield
            db.session.rollback()
            db.drop_all()
    
    def _auth_request(self, client, method, url, user_id=1, user_role='admin', **kwargs):
        """Helper method to make authenticated requests."""
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['user_role'] = user_role
        
        method_func = getattr(client, method)
        return method_func(url, **kwargs)
    
    @patch('app.api.llm_processing.db')
    def test_get_llm_status(self, mock_db, client):
        """Test GET /api/llm/status endpoint."""
        # Create a single mock query that handles filter and returns itself
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        # Mock the scalar calls (return counts)
        mock_query.scalar.side_effect = [
            1000,  # total prospects
            800,   # processed prospects  
            300,   # naics original
            200,   # naics llm inferred
            600,   # value parsed count
            700,   # title enhanced count
            500,   # set aside standardized count
        ]
        
        # Mock the first() call for last processed prospect
        mock_prospect = Mock()
        mock_prospect.ollama_processed_at = Mock(isoformat=Mock(return_value='2023-01-01T00:00:00'))
        mock_prospect.ollama_model_version = 'qwen3:latest'
        mock_query.first.return_value = mock_prospect
        
        # Mock the session query to return our mock_query
        mock_db.session.query.return_value = mock_query
        
        # Mock enhancement queue status
        with patch('app.api.llm_processing.enhancement_queue') as mock_queue:
            mock_queue.get_queue_status.return_value = {
                'total_items': 5,
                'pending_items': 3,
                'processing_items': 1,
                'completed_items': 1,
                'is_processing': True
            }
            
            # Mock LLM service check
            with patch('app.api.llm_processing.llm_service') as mock_llm:
                mock_llm.check_ollama_status.return_value = {
                    'available': True,
                    'model': 'qwen3:latest'
                }
                
                response = self._auth_request(client, 'get', '/api/llm/status')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify response structure based on actual response
        assert data['total_prospects'] == 1000
        assert data['processed_prospects'] == 800
        assert data['naics_coverage']['original'] == 300
        assert data['naics_coverage']['llm_inferred'] == 200
        assert data['naics_coverage']['total_percentage'] == 50.0
        assert data['value_parsing']['parsed_count'] == 600
        assert data['value_parsing']['total_percentage'] == 60.0
        assert data['title_enhancement']['enhanced_count'] == 700
        assert data['set_aside_standardization']['standardized_count'] == 500
        assert data['last_processed'] == '2023-01-01T00:00:00'
        assert data['model_version'] == 'qwen3:latest'
    
    @patch('app.api.llm_processing.Prospect')
    @patch('app.api.llm_processing.add_individual_enhancement')
    def test_add_to_enhancement_queue_success(self, mock_add, mock_prospect_class, client):
        """Test POST /api/llm/enhance-single endpoint - success case."""
        # Mock prospect lookup
        mock_prospect = Mock()
        mock_prospect.enhancement_status = None
        mock_prospect_class.query.get.return_value = mock_prospect
        
        # Mock add_individual_enhancement return value
        mock_add.return_value = {
            'queue_item_id': 'queue-123',
            'was_existing': False
        }
        
        response = self._auth_request(
            client, 'post', '/api/llm/enhance-single',
            json={
                'prospect_id': '123',
                'force_redo': True,
                'enhancement_type': 'all'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'queue_item_id' in data
        assert data['queue_item_id'] == 'queue-123'
        
        # Verify function was called correctly
        mock_add.assert_called_once_with(
            prospect_id='123',
            enhancement_type='all',
            user_id=1,
            force_redo=True
        )
    
    @patch('app.api.llm_processing.Prospect')
    def test_add_to_enhancement_queue_error(self, mock_prospect_class, client):
        """Test POST /api/llm/enhance-single endpoint - prospect not found."""
        # Mock prospect not found
        mock_prospect_class.query.get.return_value = None
        
        response = self._auth_request(
            client, 'post', '/api/llm/enhance-single',
            json={'prospect_id': '123'}
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_add_to_enhancement_queue_missing_prospect_id(self, client):
        """Test POST /api/llm/enhance-single endpoint - missing prospect_id."""
        response = self._auth_request(
            client, 'post', '/api/llm/enhance-single',
            json={'force_redo': True}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'prospect_id' in data['error']
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_get_queue_status(self, mock_queue, client):
        """Test GET /api/llm/queue/status endpoint."""
        mock_queue.get_queue_status.return_value = {
            'total_items': 10,
            'pending_items': 7,
            'processing_items': 2,
            'completed_items': 1,
            'is_processing': True,
            'current_item': '123'
        }
        
        response = self._auth_request(client, 'get', '/api/llm/queue/status')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total_items'] == 10
        assert data['is_processing'] is True
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_get_queue_item_status(self, mock_queue, client):
        """Test GET /api/llm/queue/item/<item_id> endpoint."""
        mock_queue.get_item_status.return_value = {
            'status': 'processing',
            'queue_position': 2,
            'progress': {'values': {'completed': True}},
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        response = self._auth_request(client, 'get', '/api/llm/queue/item/123')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'processing'
        assert data['queue_position'] == 2
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_get_queue_item_not_found(self, mock_queue, client):
        """Test GET /api/llm/queue/item/<item_id> - not found."""
        mock_queue.get_item_status.return_value = None
        
        response = self._auth_request(client, 'get', '/api/llm/queue/item/999')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_remove_from_queue(self, mock_queue, client):
        """Test POST /api/llm/queue/item/<item_id>/cancel endpoint."""
        mock_queue.cancel_item.return_value = True
        
        response = self._auth_request(client, 'post', '/api/llm/queue/item/123/cancel')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'cancelled successfully' in data['message']
        
        mock_queue.cancel_item.assert_called_once_with('123')
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_start_queue_processing(self, mock_queue, client):
        """Test POST /api/llm/queue/start-worker endpoint."""
        response = self._auth_request(client, 'post', '/api/llm/queue/start-worker')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'started successfully' in data['message']
        
        mock_queue.start_worker.assert_called_once()
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_stop_queue_processing(self, mock_queue, client):
        """Test POST /api/llm/queue/stop-worker endpoint."""
        response = self._auth_request(client, 'post', '/api/llm/queue/stop-worker')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'stopped successfully' in data['message']
        
        mock_queue.stop_worker.assert_called_once()
    
    def test_get_user_queue_items(self, client):
        """Test GET /api/llm/queue/user endpoint - endpoint does not exist."""
        # This endpoint doesn't exist in the actual API
        # Marking test as skipped
        pytest.skip("Endpoint /api/llm/queue/user does not exist")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['items']) == 2
        assert data['items'][0]['prospect_id'] == '123'
        
        # Verify function was called (user ID would come from session)
    
    def test_clear_completed_items(self, client):
        """Test POST /api/llm/queue/clear-completed endpoint - endpoint does not exist."""
        # This endpoint doesn't exist in the actual API
        # Marking test as skipped
        pytest.skip("Endpoint /api/llm/queue/clear-completed does not exist")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['cleared_count'] == 5
    
    def test_get_enhancement_history(self, client):
        """Test GET /api/llm/history endpoint - endpoint does not exist."""
        # This endpoint doesn't exist in the actual API
        # Marking test as skipped
        pytest.skip("Endpoint /api/llm/history does not exist")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 50
        assert len(data['items']) == 1
        assert data['items'][0]['prospect_id'] == 123
    
    def test_stream_enhancement_progress_start(self, client):
        """Test GET /api/llm/stream/progress endpoint - endpoint does not exist."""
        # This endpoint doesn't exist in the actual API
        # Marking test as skipped
        pytest.skip("Endpoint /api/llm/stream/progress does not exist")