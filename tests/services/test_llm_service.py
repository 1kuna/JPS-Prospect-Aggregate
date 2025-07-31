"""
Comprehensive unit tests for LLM Service.

Tests cover all critical functionality of the unified LLM service to prevent
breaking changes during refactoring.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
from decimal import Decimal
import json
import threading
import time

from app import create_app
from app.services.llm_service import LLMService
from app.database.models import Prospect, InferredProspectData, LLMOutput
from app.services.set_aside_standardization import StandardSetAside


class TestLLMService:
    """Test suite for LLMService."""
    
    @pytest.fixture(scope='class')
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def app_context(self, app):
        """Create Flask app context."""
        with app.app_context():
            yield
    
    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance for testing."""
        return LLMService(model_name='test_model', batch_size=10)
    
    @pytest.fixture
    def mock_prospect(self):
        """Create a mock prospect for testing."""
        prospect = Mock()
        prospect.id = 1
        prospect.title = "Test Contract Opportunity"
        prospect.description = "This is a test description for IT services"
        prospect.set_aside = "Small Business Set-Aside"
        prospect.estimated_value_text = "$100,000 - $500,000"
        prospect.estimated_value_single = None
        prospect.naics = None
        prospect.naics_source = None
        prospect.ollama_processed_at = None
        prospect.title_enhanced = None
        prospect.set_aside_parsed = None
        return prospect
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.add = Mock()
        session.merge = Mock()
        session.query = Mock()
        session.execute = Mock()
        return session
    
    def test_init(self, llm_service):
        """Test LLMService initialization."""
        assert llm_service.model_name == 'test_model'
        assert llm_service.batch_size == 10
        assert llm_service._processing is False
        assert llm_service._thread is None
        assert llm_service.set_aside_standardizer is not None
    
    def test_check_ollama_status(self, llm_service, app_context):
        """Test checking Ollama service status."""
        with patch('app.services.llm_service.call_ollama') as mock_call:
            # Test successful connection
            mock_call.return_value = "Test response"
            status = llm_service.check_ollama_status()
            assert status['available'] is True
            assert status['model'] == 'test_model'
            assert 'error' not in status
            
            # Test connection failure
            mock_call.side_effect = Exception("Connection failed")
            status = llm_service.check_ollama_status()
            assert status['available'] is False
            assert 'error' in status
            assert "Connection failed" in status['error']
    
    @patch('app.services.llm_service.db')
    def test_enhance_prospect_individual(self, mock_db, llm_service, mock_prospect, app_context):
        """Test individual prospect enhancement."""
        mock_db.session = Mock()
        
        with patch('app.services.llm_service.call_ollama') as mock_call:
            # Mock LLM responses
            mock_call.side_effect = [
                '{"min_value": 100000, "max_value": 500000}',  # Value parsing
                'IT Services and Software Development',  # Title enhancement
                '541511',  # NAICS code
            ]
            
            # Mock NAICS validation
            with patch('app.services.llm_service.validate_naics_code', return_value=True):
                with patch('app.services.llm_service.get_naics_description', return_value='Custom Computer Programming Services'):
                    result = llm_service.enhance_prospect(mock_prospect, enhancement_types=['values', 'titles', 'naics'])
        
        # Verify enhancements were applied
        assert result is True
        assert mock_prospect.estimated_value_single == 300000  # Average of min/max
        assert mock_prospect.title_enhanced == 'IT Services and Software Development'
        assert mock_prospect.naics == '541511'
        assert mock_prospect.naics_source == 'llm_inferred'
        assert mock_prospect.ollama_processed_at is not None
        
        # Verify LLM was called correctly
        assert mock_call.call_count == 3
    
    def test_parse_contract_value(self, llm_service, app_context):
        """Test contract value parsing logic."""
        with patch('app.services.llm_service.call_ollama') as mock_call:
            # Test successful parsing
            mock_call.return_value = '{"min_value": 50000, "max_value": 150000}'
            result = llm_service._parse_contract_value("$50k - $150k")
            assert result == {'min_value': 50000, 'max_value': 150000, 'avg_value': 100000}
            
            # Test invalid JSON response
            mock_call.return_value = 'Invalid JSON'
            result = llm_service._parse_contract_value("$50k - $150k")
            assert result is None
            
            # Test LLM error
            mock_call.side_effect = Exception("LLM error")
            result = llm_service._parse_contract_value("$50k - $150k")
            assert result is None
    
    def test_classify_naics(self, llm_service, app_context):
        """Test NAICS classification."""
        with patch('app.services.llm_service.call_ollama') as mock_call:
            # Test valid NAICS code
            mock_call.return_value = '541512'
            with patch('app.services.llm_service.validate_naics_code', return_value=True):
                with patch('app.services.llm_service.get_naics_description', return_value='Computer Systems Design Services'):
                    result = llm_service._classify_naics("IT consulting services", "Computer systems integration")
                    assert result == {'code': '541512', 'description': 'Computer Systems Design Services'}
            
            # Test invalid NAICS code
            mock_call.return_value = '999999'
            with patch('app.services.llm_service.validate_naics_code', return_value=False):
                result = llm_service._classify_naics("IT consulting services", "Computer systems integration")
                assert result is None
    
    def test_standardize_set_aside(self, llm_service, app_context):
        """Test set-aside standardization."""
        # Test various set-aside formats
        test_cases = [
            ("Small Business Set-Aside", StandardSetAside.SMALL_BUSINESS),
            ("8(a) Set-Aside", StandardSetAside.EIGHT_A),
            ("WOSB", StandardSetAside.WOSB),
            ("HUBZone Set-Aside", StandardSetAside.HUBZONE),
            ("SDVOSB Set-Aside", StandardSetAside.SDVOSB),
            ("Full and Open", StandardSetAside.FULL_AND_OPEN),
            ("Unknown Format", StandardSetAside.UNKNOWN),
        ]
        
        for input_text, expected in test_cases:
            result = llm_service._standardize_set_aside(input_text)
            assert result == expected.value
    
    @patch('app.services.llm_service.db')
    def test_process_batch(self, mock_db, llm_service, app_context):
        """Test batch processing of prospects."""
        # Create mock prospects
        prospects = [Mock() for _ in range(5)]
        for i, p in enumerate(prospects):
            p.id = i + 1
            p.title = f"Contract {i+1}"
            p.description = f"Description {i+1}"
            p.estimated_value_text = f"${(i+1)*100000}"
            p.estimated_value_single = None
            p.naics = None
            p.ollama_processed_at = None
        
        mock_db.session = Mock()
        mock_db.session.commit = Mock()
        
        with patch.object(llm_service, 'enhance_prospect') as mock_enhance:
            mock_enhance.return_value = True
            
            # Process batch
            llm_service.process_batch(
                prospects, 
                enhancement_types=['values', 'titles'],
                progress_callback=None
            )
            
            # Verify all prospects were processed
            assert mock_enhance.call_count == 5
            assert mock_db.session.commit.call_count >= 1
    
    def test_iterative_processing_start_stop(self, llm_service, app_context):
        """Test starting and stopping iterative processing."""
        with patch.object(llm_service, '_run_iterative_processing') as mock_run:
            # Start processing
            llm_service.start_iterative_processing(
                limit=100,
                enhancement_types=['values']
            )
            
            assert llm_service._processing is True
            assert llm_service._thread is not None
            assert llm_service._thread.is_alive()
            
            # Stop processing
            llm_service.stop_iterative_processing()
            time.sleep(0.1)  # Give thread time to stop
            
            assert llm_service._processing is False
            assert llm_service._stop_event.is_set()
    
    @patch('app.services.llm_service.db')
    def test_get_progress_stats(self, mock_db, llm_service, app_context):
        """Test progress statistics calculation."""
        # Mock query results
        mock_query = Mock()
        mock_query.scalar.side_effect = [1000, 800, 600, 700, 500]  # total, processed, naics, values, titles
        mock_db.session.query.return_value = mock_query
        
        stats = llm_service.get_progress_stats()
        
        assert stats['total_prospects'] == 1000
        assert stats['processed_prospects'] == 800
        assert stats['progress_percentage'] == 80.0
        assert stats['naics_coverage'] == 600
        assert stats['value_coverage'] == 700
        assert stats['title_coverage'] == 500
    
    @patch('app.services.llm_service.db')
    def test_log_llm_output(self, mock_db, llm_service, app_context):
        """Test logging LLM output to database."""
        mock_db.session = Mock()
        
        llm_service._log_llm_output(
            prospect_id=1,
            prompt_type='value_parsing',
            prompt='Parse this value',
            response='{"min_value": 100000}',
            model_name='test_model'
        )
        
        # Verify LLMOutput was created and added to session
        assert mock_db.session.add.called
        llm_output = mock_db.session.add.call_args[0][0]
        assert isinstance(llm_output, LLMOutput)
        assert llm_output.prospect_id == 1
        assert llm_output.prompt_type == 'value_parsing'
        assert llm_output.response == '{"min_value": 100000}'
    
    def test_enhancement_with_errors(self, llm_service, mock_prospect, app_context):
        """Test enhancement handles errors gracefully."""
        with patch('app.services.llm_service.call_ollama') as mock_call:
            # Simulate LLM failures
            mock_call.side_effect = [
                Exception("LLM connection error"),  # Value parsing fails
                "Enhanced Title",  # Title works
                Exception("NAICS lookup failed"),  # NAICS fails
            ]
            
            with patch('app.services.llm_service.db'):
                result = llm_service.enhance_prospect(
                    mock_prospect, 
                    enhancement_types=['values', 'titles', 'naics']
                )
            
            # Should still return True if at least one enhancement worked
            assert result is True
            assert mock_prospect.title_enhanced == "Enhanced Title"
            # Values and NAICS should remain unchanged due to errors
            assert mock_prospect.estimated_value_single is None
            assert mock_prospect.naics is None
    
    def test_concurrent_enhancement_safety(self, llm_service, app):
        """Test thread safety of enhancement operations."""
        results = []
        errors = []
        
        def enhance_prospect_thread(prospect_id):
            try:
                with app.app_context():
                    prospect = Mock()
                    prospect.id = prospect_id
                    prospect.title = f"Contract {prospect_id}"
                    prospect.estimated_value_text = "$100k"
                
                with patch('app.services.llm_service.call_ollama', return_value='{"min_value": 100000}'):
                    with patch('app.services.llm_service.db'):
                        result = llm_service.enhance_prospect(prospect, enhancement_types=['values'])
                        results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=enhance_prospect_thread, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify no errors and all succeeded
        assert len(errors) == 0
        assert all(results)
        assert len(results) == 10