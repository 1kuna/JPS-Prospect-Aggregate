"""
Unit tests for LLM Processing API endpoints.

Tests all endpoints in the llm_processing blueprint to ensure API stability.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json
from flask import Flask

from app.api.llm_processing import llm_bp
from app.services.enhancement_queue import QueueStatus


class TestLLMProcessingAPI:
    """Test suite for LLM processing API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(llm_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def admin_headers(self):
        """Mock admin authentication headers."""
        return {'X-Admin-Token': 'test-admin-token'}
    
    @pytest.fixture
    def mock_admin_required(self):
        """Mock the admin_required decorator to allow all requests."""
        def decorator(f):
            return f
        with patch('app.api.llm_processing.admin_required', decorator):
            yield
    
    @patch('app.api.llm_processing.db')
    def test_get_llm_status(self, mock_db, client, mock_admin_required):
        """Test GET /api/llm/status endpoint."""
        # Mock database queries
        mock_query = Mock()
        mock_query.scalar.side_effect = [
            1000,  # total prospects
            800,   # processed prospects
            300,   # naics original
            200,   # naics llm inferred
            600,   # value parsed count
        ]
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
                
                response = client.get('/api/llm/status', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify response structure
        assert data['total_prospects'] == 1000
        assert data['processed_prospects'] == 800
        assert data['processing_percentage'] == 80.0
        assert data['naics_coverage']['original'] == 300
        assert data['naics_coverage']['llm_inferred'] == 200
        assert data['naics_coverage']['total'] == 500
        assert data['naics_coverage']['percentage'] == 50.0
        assert data['value_parsing']['parsed_count'] == 600
        assert data['value_parsing']['percentage'] == 60.0
        assert data['llm_status']['available'] is True
        assert data['queue_status']['total_items'] == 5
    
    @patch('app.api.llm_processing.add_individual_enhancement')
    def test_add_to_enhancement_queue_success(self, mock_add, client, mock_admin_required):
        """Test POST /api/llm/enhance endpoint - success case."""
        mock_add.return_value = {
            'success': True,
            'queue_position': 3,
            'message': 'Added to enhancement queue at position 3'
        }
        
        response = client.post(
            '/api/llm/enhance',
            json={
                'prospect_id': '123',
                'force_redo': True,
                'enhancement_types': ['values', 'titles']
            },
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['queue_position'] == 3
        
        # Verify function was called correctly
        mock_add.assert_called_once()
        call_args = mock_add.call_args[1]
        assert call_args['prospect_id'] == '123'
        assert call_args['force_redo'] is True
        assert call_args['enhancement_types'] == ['values', 'titles']
    
    @patch('app.api.llm_processing.add_individual_enhancement')
    def test_add_to_enhancement_queue_error(self, mock_add, client, mock_admin_required):
        """Test POST /api/llm/enhance endpoint - error case."""
        mock_add.return_value = {
            'success': False,
            'error': 'Queue is full'
        }
        
        response = client.post(
            '/api/llm/enhance',
            json={'prospect_id': '123'},
            headers=admin_headers
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Queue is full' in data['error']
    
    def test_add_to_enhancement_queue_missing_prospect_id(self, client, mock_admin_required):
        """Test POST /api/llm/enhance endpoint - missing prospect_id."""
        response = client.post(
            '/api/llm/enhance',
            json={'force_redo': True},
            headers=admin_headers
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'prospect_id' in data['error']
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_get_queue_status(self, mock_queue, client, mock_admin_required):
        """Test GET /api/llm/queue/status endpoint."""
        mock_queue.get_queue_status.return_value = {
            'total_items': 10,
            'pending_items': 7,
            'processing_items': 2,
            'completed_items': 1,
            'is_processing': True,
            'current_item': '123'
        }
        
        response = client.get('/api/llm/queue/status', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total_items'] == 10
        assert data['is_processing'] is True
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_get_queue_item_status(self, mock_queue, client, mock_admin_required):
        """Test GET /api/llm/queue/item/<prospect_id> endpoint."""
        mock_queue.get_item_status.return_value = {
            'status': 'processing',
            'queue_position': 2,
            'progress': {'values': {'completed': True}},
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        response = client.get('/api/llm/queue/item/123', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'processing'
        assert data['queue_position'] == 2
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_get_queue_item_not_found(self, mock_queue, client, mock_admin_required):
        """Test GET /api/llm/queue/item/<prospect_id> - not found."""
        mock_queue.get_item_status.return_value = None
        
        response = client.get('/api/llm/queue/item/999', headers=admin_headers)
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_remove_from_queue(self, mock_queue, client, mock_admin_required):
        """Test DELETE /api/llm/queue/item/<prospect_id> endpoint."""
        mock_queue.remove_from_queue.return_value = True
        
        response = client.delete('/api/llm/queue/item/123', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        mock_queue.remove_from_queue.assert_called_once_with('123')
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_start_queue_processing(self, mock_queue, client, mock_admin_required):
        """Test POST /api/llm/queue/start endpoint."""
        response = client.post('/api/llm/queue/start', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'started' in data['message']
        
        mock_queue.start_processing.assert_called_once()
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_stop_queue_processing(self, mock_queue, client, mock_admin_required):
        """Test POST /api/llm/queue/stop endpoint."""
        response = client.post('/api/llm/queue/stop', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'stopped' in data['message']
        
        mock_queue.stop_processing.assert_called_once()
    
    @patch('app.api.llm_processing.enhancement_queue')
    @patch('app.api.llm_processing.get_current_user')
    def test_get_user_queue_items(self, mock_user, mock_queue, client, mock_admin_required):
        """Test GET /api/llm/queue/user endpoint."""
        mock_user.return_value = Mock(id=1)
        mock_queue.get_user_items.return_value = [
            {
                'prospect_id': '123',
                'status': 'pending',
                'queue_position': 3,
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'prospect_id': '456',
                'status': 'processing',
                'queue_position': 1,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        ]
        
        response = client.get('/api/llm/queue/user', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['items']) == 2
        assert data['items'][0]['prospect_id'] == '123'
        
        mock_queue.get_user_items.assert_called_once_with(1)
    
    @patch('app.api.llm_processing.enhancement_queue')
    def test_clear_completed_items(self, mock_queue, client, mock_admin_required):
        """Test POST /api/llm/queue/clear-completed endpoint."""
        mock_queue.clear_completed_items.return_value = 5
        
        response = client.post('/api/llm/queue/clear-completed', headers=admin_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['cleared_count'] == 5
    
    @patch('app.api.llm_processing.db')
    def test_get_enhancement_history(self, mock_db, client, mock_admin_required):
        """Test GET /api/llm/history endpoint."""
        # Mock the query results
        mock_log1 = Mock()
        mock_log1.id = 1
        mock_log1.prospect_id = 123
        mock_log1.action = 'enhancement_requested'
        mock_log1.created_at = datetime.now(timezone.utc)
        mock_log1.user_id = 1
        mock_log1.details = {'enhancement_types': ['values']}
        
        mock_query = Mock()
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [mock_log1]
        mock_query.count.return_value = 50
        mock_db.session.query.return_value = mock_query
        
        response = client.get(
            '/api/llm/history?limit=20&offset=0&prospect_id=123',
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 50
        assert len(data['items']) == 1
        assert data['items'][0]['prospect_id'] == 123
    
    def test_stream_enhancement_progress_start(self, client, mock_admin_required):
        """Test GET /api/llm/stream/progress endpoint."""
        with patch('app.api.llm_processing.enhancement_queue') as mock_queue:
            # Simulate a few status updates
            statuses = [
                {
                    'total_items': 5,
                    'processing_items': 1,
                    'current_item': '123',
                    'current_step': 'Processing values'
                },
                {
                    'total_items': 5,
                    'processing_items': 1,
                    'current_item': '123',
                    'current_step': 'Processing titles'
                }
            ]
            mock_queue.get_queue_status.side_effect = statuses
            
            # Make request and consume some events
            response = client.get('/api/llm/stream/progress', headers=admin_headers)
            assert response.status_code == 200
            
            # Read a couple of events from the stream
            events = []
            for data in response.response:
                events.append(data)
                if len(events) >= 2:
                    break
            
            # Verify SSE format
            assert b'data:' in events[0]
            assert b'current_step' in events[0]