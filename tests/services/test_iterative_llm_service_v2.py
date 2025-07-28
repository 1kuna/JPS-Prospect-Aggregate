"""
Unit tests for IterativeLLMServiceV2 - Real-time processing with threading
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import threading
import time
from datetime import datetime, timezone

from app.services.iterative_llm_service_v2 import IterativeLLMServiceV2, EnhancementType
from app.services.base_llm_service import BaseLLMService
from app.database.models import Prospect


class TestIterativeLLMServiceV2Initialization:
    """Test service initialization and basic properties"""
    
    def test_initialization(self):
        """Test service initializes correctly"""
        service = IterativeLLMServiceV2()
        
        assert isinstance(service.base_service, BaseLLMService)
        assert service._processing is False
        assert service._thread is None
        assert isinstance(service._stop_event, threading.Event)
        assert service._queue_service is None
        assert service._emit_callback is None
        
        # Check initial progress state
        progress = service.get_progress()
        assert progress['status'] == 'idle'
        assert progress['processed'] == 0
        assert progress['total'] == 0
    
    def test_is_processing_initial_state(self):
        """Test initial processing state"""
        service = IterativeLLMServiceV2()
        assert service.is_processing() is False
    
    def test_set_queue_service(self):
        """Test setting queue service"""
        service = IterativeLLMServiceV2()
        mock_queue_service = Mock()
        
        service.set_queue_service(mock_queue_service)
        
        assert service._queue_service == mock_queue_service
    
    def test_set_emit_callback(self):
        """Test setting emit callback"""
        service = IterativeLLMServiceV2()
        mock_callback = Mock()
        
        service.set_emit_callback(mock_callback)
        
        assert service._emit_callback == mock_callback


class TestBuildEnhancementFilter:
    """Test enhancement filter building logic"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMServiceV2()
    
    def test_build_filter_values_with_skip_existing(self, service):
        """Test building filter for values enhancement with skip_existing=True"""
        filter_condition = service._build_enhancement_filter("values", skip_existing=True)
        
        # Should return a SQLAlchemy filter condition
        assert filter_condition is not None
        # The actual filter logic is tested through integration
    
    def test_build_filter_naics_with_skip_existing(self, service):
        """Test building filter for NAICS enhancement with skip_existing=True"""
        filter_condition = service._build_enhancement_filter("naics", skip_existing=True)
        
        assert filter_condition is not None
    
    def test_build_filter_titles_with_skip_existing(self, service):
        """Test building filter for titles enhancement with skip_existing=True"""
        filter_condition = service._build_enhancement_filter("titles", skip_existing=True)
        
        assert filter_condition is not None
    
    def test_build_filter_set_asides_with_skip_existing(self, service):
        """Test building filter for set_asides enhancement with skip_existing=True"""
        filter_condition = service._build_enhancement_filter("set_asides", skip_existing=True)
        
        assert filter_condition is not None
    
    def test_build_filter_all_with_skip_existing(self, service):
        """Test building filter for all enhancements with skip_existing=True"""
        filter_condition = service._build_enhancement_filter("all", skip_existing=True)
        
        assert filter_condition is not None
    
    def test_build_filter_without_skip_existing(self, service):
        """Test building filter without skipping existing enhancements"""
        filter_condition = service._build_enhancement_filter("values", skip_existing=False)
        
        assert filter_condition is not None


class TestGetProspectsToProcess:
    """Test prospect retrieval for processing"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMServiceV2()
    
    @patch('app.services.iterative_llm_service_v2.Session')
    def test_get_prospects_to_process_with_filter(self, mock_session_class, service):
        """Test getting prospects to process with valid filter"""
        mock_db_session = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.all.return_value = ["prospect1", "prospect2"]
        
        with patch.object(service, '_build_enhancement_filter') as mock_build_filter:
            mock_build_filter.return_value = "some_filter"
            
            result = service._get_prospects_to_process("values", mock_db_session)
            
            assert result == ["prospect1", "prospect2"]
            mock_build_filter.assert_called_once_with("values", True)
    
    @patch('app.services.iterative_llm_service_v2.Session')
    def test_get_prospects_to_process_no_filter(self, mock_session_class, service):
        """Test getting prospects when filter returns None"""
        mock_db_session = Mock()
        
        with patch.object(service, '_build_enhancement_filter') as mock_build_filter:
            mock_build_filter.return_value = None
            
            result = service._get_prospects_to_process("invalid_type", mock_db_session)
            
            assert result == []


class TestStartEnhancement:
    """Test starting enhancement processes"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMServiceV2()
    
    def test_start_enhancement_already_processing(self, service):
        """Test starting enhancement when already processing"""
        service._processing = True
        
        result = service.start_enhancement("values")
        
        assert result["status"] == "error"
        assert "already in progress" in result["message"]
    
    @patch('app.services.iterative_llm_service_v2.create_app')
    @patch('app.services.iterative_llm_service_v2.sessionmaker')
    def test_start_enhancement_no_prospects(self, mock_sessionmaker, mock_create_app, service):
        """Test starting enhancement when no prospects need processing"""
        # Setup mocks
        mock_app = Mock()
        mock_create_app.return_value = mock_app
        mock_app.app_context.return_value.__enter__ = Mock()
        mock_app.app_context.return_value.__exit__ = Mock()
        
        mock_session = Mock()
        mock_sessionmaker.return_value = mock_session
        
        with patch.object(service, '_get_prospects_to_process') as mock_get_prospects:
            mock_get_prospects.return_value = []
            
            result = service.start_enhancement("values")
            
            assert result["status"] == "completed"
            assert result["total_to_process"] == 0
    
    @patch('app.services.iterative_llm_service_v2.create_app')
    @patch('app.services.iterative_llm_service_v2.sessionmaker')
    def test_start_enhancement_with_queue_service(self, mock_sessionmaker, mock_create_app, service):
        """Test starting enhancement with queue service"""
        # Setup service with queue
        mock_queue_service = Mock()
        mock_queue_service.add_bulk_enhancement.return_value = "queue-item-123"
        service.set_queue_service(mock_queue_service)
        
        # Setup mocks
        mock_app = Mock()
        mock_create_app.return_value = mock_app
        mock_app.app_context.return_value.__enter__ = Mock()
        mock_app.app_context.return_value.__exit__ = Mock()
        
        mock_session = Mock()
        mock_sessionmaker.return_value = mock_session
        
        mock_prospects = [Mock(id="prospect-1"), Mock(id="prospect-2")]
        
        with patch.object(service, '_get_prospects_to_process') as mock_get_prospects:
            mock_get_prospects.return_value = mock_prospects
            
            result = service.start_enhancement("values")
            
            assert result["status"] == "queued"
            assert result["total_to_process"] == 2
            assert result["queue_item_id"] == "queue-item-123"
            assert service._processing is True


class TestStopEnhancement:
    """Test stopping enhancement processes"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMServiceV2()
    
    def test_stop_enhancement_not_processing(self, service):
        """Test stopping when not processing"""
        result = service.stop_enhancement()
        
        assert result["status"] == "idle"
        assert "No enhancement process running" in result["message"]
    
    def test_stop_enhancement_while_processing(self, service):
        """Test stopping while processing"""
        service._processing = True
        mock_thread = Mock()
        mock_thread.is_alive.return_value = False
        service._thread = mock_thread
        
        result = service.stop_enhancement()
        
        assert result["status"] == "stopped"
        assert service._processing is False
        assert service._stop_event.is_set()


class TestProgressTracking:
    """Test progress tracking functionality"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMServiceV2()
    
    def test_get_progress_thread_safe(self, service):
        """Test that get_progress returns a copy and is thread-safe"""
        # Modify internal progress
        with service._lock:
            service._progress["test_field"] = "test_value"
        
        progress1 = service.get_progress()
        progress2 = service.get_progress()
        
        # Should get copies, not the same object
        assert progress1 is not progress2
        assert progress1["test_field"] == "test_value"
        
        # Modifying returned progress shouldn't affect internal state
        progress1["test_field"] = "modified"
        progress3 = service.get_progress()
        assert progress3["test_field"] == "test_value"


class TestMonitorQueueProgress:
    """Test queue progress monitoring"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMServiceV2()
    
    def test_monitor_queue_progress_updates_progress(self, service):
        """Test that queue monitoring updates local progress"""
        mock_queue_service = Mock()
        mock_queue_service.get_item_status.return_value = {
            "status": "processing",
            "progress": {"processed": 5, "total": 10}
        }
        service.set_queue_service(mock_queue_service)
        service._processing = True
        
        # Start monitoring in a separate thread for a short time
        monitor_thread = threading.Thread(
            target=service._monitor_queue_progress,
            args=("test-queue-item",),
            daemon=True
        )
        monitor_thread.start()
        
        # Give it a moment to update
        time.sleep(0.1)
        service._stop_event.set()  # Stop monitoring
        monitor_thread.join(timeout=1)
        
        # Check that progress was updated
        progress = service.get_progress()
        assert progress["status"] == "processing"
        assert progress["processed"] == 5
        assert progress["total"] == 10
    
    def test_monitor_queue_progress_completion(self, service):
        """Test that monitoring stops on completion"""
        mock_queue_service = Mock()
        mock_queue_service.get_item_status.return_value = {
            "status": "completed",
            "progress": {"processed": 10, "total": 10}
        }
        service.set_queue_service(mock_queue_service)
        service._processing = True
        
        # Start monitoring
        monitor_thread = threading.Thread(
            target=service._monitor_queue_progress,
            args=("test-queue-item",),
            daemon=True
        )
        monitor_thread.start()
        
        # Give it time to process completion
        monitor_thread.join(timeout=1)
        
        # Should have stopped processing
        assert service._processing is False


class TestDirectProcessing:
    """Test direct processing fallback"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMServiceV2()
    
    @patch('app.services.iterative_llm_service_v2.sessionmaker')
    def test_start_direct_processing(self, mock_sessionmaker, service):
        """Test starting direct processing"""
        mock_app = Mock()
        mock_app.app_context.return_value.__enter__ = Mock()
        mock_app.app_context.return_value.__exit__ = Mock()
        
        mock_session = Mock()
        mock_sessionmaker.return_value = mock_session
        
        with patch.object(service, '_count_unprocessed') as mock_count:
            mock_count.return_value = 5
            
            result = service._start_direct_processing("values", mock_app)
            
            assert result["status"] == "started"
            assert result["total_to_process"] == 5
            assert service._processing is True


class TestProcessIteratively:
    """Test the iterative processing loop"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMServiceV2()
    
    @patch('app.services.iterative_llm_service_v2.sessionmaker')
    @patch('app.services.iterative_llm_service_v2.AIEnrichmentLog')
    def test_process_iteratively_single_prospect(self, mock_log_class, mock_sessionmaker, service):
        """Test processing a single prospect iteratively"""
        mock_app = Mock()
        mock_app.app_context.return_value.__enter__ = Mock()
        mock_app.app_context.return_value.__exit__ = Mock()
        
        mock_session = Mock()
        mock_sessionmaker.return_value = mock_session
        
        # Mock single prospect
        mock_prospect = Mock()
        mock_prospect.id = "test-prospect"
        mock_prospect.title = "Test Title"
        
        call_count = 0
        def mock_get_next_prospect(*args):
            nonlocal call_count
            call_count += 1
            return mock_prospect if call_count == 1 else None
        
        with patch.object(service, '_get_next_prospect', side_effect=mock_get_next_prospect), \
             patch.object(service.base_service, 'process_single_prospect_enhancement') as mock_process_single:
            
            mock_process_single.return_value = {'values': True, 'naics': False, 'titles': False, 'set_asides': False}
            
            # Set up initial state
            service._processing = True
            service._progress["started_at"] = datetime.now(timezone.utc).isoformat()
            service._progress["total"] = 1
            
            # Process iteratively
            service._process_iteratively("values", mock_app)
            
            # Verify processing occurred
            mock_process_single.assert_called_once()
            assert service._processing is False
            assert service._progress["status"] == "completed"
            assert service._progress["processed"] == 1
    
    @patch('app.services.iterative_llm_service_v2.sessionmaker')
    def test_process_iteratively_with_progress_callback(self, mock_sessionmaker, service):
        """Test processing with progress callback"""
        mock_app = Mock()
        mock_app.app_context.return_value.__enter__ = Mock()
        mock_app.app_context.return_value.__exit__ = Mock()
        
        mock_session = Mock()
        mock_sessionmaker.return_value = mock_session
        
        mock_prospect = Mock()
        mock_prospect.id = "test-prospect"
        mock_prospect.title = "Test Title"
        
        # Mock emit callback
        mock_emit_callback = Mock()
        service.set_emit_callback(mock_emit_callback)
        
        call_count = 0
        def mock_get_next_prospect(*args):
            nonlocal call_count
            call_count += 1
            return mock_prospect if call_count == 1 else None
        
        with patch.object(service, '_get_next_prospect', side_effect=mock_get_next_prospect), \
             patch.object(service.base_service, 'process_single_prospect_enhancement') as mock_process_single, \
             patch('app.services.iterative_llm_service_v2.emit_field_update') as mock_emit_field_update:
            
            def mock_process_with_callback(prospect, enhancement_type, progress_callback=None):
                if progress_callback:
                    progress_callback({"status": "processing", "field": "values", "prospect_id": prospect.id})
                return {'values': True, 'naics': False, 'titles': False, 'set_asides': False}
            
            mock_process_single.side_effect = mock_process_with_callback
            
            service._processing = True
            service._progress["started_at"] = datetime.now(timezone.utc).isoformat()
            
            service._process_iteratively("values", mock_app)
            
            # Verify emit_field_update was called
            mock_emit_field_update.assert_called_once()


class TestCountUnprocessed:
    """Test counting unprocessed prospects"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMServiceV2()
    
    def test_count_unprocessed_with_filter(self, service):
        """Test counting unprocessed prospects with valid filter"""
        mock_session = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.count.return_value = 42
        
        with patch.object(service, '_build_enhancement_filter') as mock_build_filter:
            mock_build_filter.return_value = "some_filter"
            
            result = service._count_unprocessed("values", mock_session)
            
            assert result == 42
    
    def test_count_unprocessed_no_filter(self, service):
        """Test counting when filter returns None"""
        mock_session = Mock()
        
        with patch.object(service, '_build_enhancement_filter') as mock_build_filter:
            mock_build_filter.return_value = None
            
            result = service._count_unprocessed("invalid_type", mock_session)
            
            assert result == 0


class TestGetNextProspect:
    """Test getting next prospect for processing"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMServiceV2()
    
    def test_get_next_prospect_with_filter(self, service):
        """Test getting next prospect with valid filter"""
        mock_session = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.first.return_value = "next_prospect"
        
        with patch.object(service, '_build_enhancement_filter') as mock_build_filter:
            mock_build_filter.return_value = "some_filter"
            
            result = service._get_next_prospect("values", mock_session)
            
            assert result == "next_prospect"
    
    def test_get_next_prospect_no_filter(self, service):
        """Test getting next prospect when filter returns None"""
        mock_session = Mock()
        
        with patch.object(service, '_build_enhancement_filter') as mock_build_filter:
            mock_build_filter.return_value = None
            
            result = service._get_next_prospect("invalid_type", mock_session)
            
            assert result is None