"""
Unit tests for LLM Service Utilities - Shared utility functions
"""

import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime, timezone

from app.services.llm_service_utils import (
    ensure_extra_is_dict,
    update_prospect_timestamps,
    emit_field_update,
    calculate_progress_percentage,
    format_duration,
    get_enhancement_field_names,
    should_skip_prospect,
    create_enhancement_summary
)
from app.database.models import Prospect


class TestEnsureExtraIsDict:
    """Test ensure_extra_is_dict function"""
    
    @pytest.fixture
    def mock_prospect(self):
        """Create a mock prospect for testing"""
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect"
        return prospect
    
    def test_ensure_extra_none(self, mock_prospect):
        """Test when extra is None"""
        mock_prospect.extra = None
        
        ensure_extra_is_dict(mock_prospect)
        
        assert mock_prospect.extra == {}
    
    def test_ensure_extra_already_dict(self, mock_prospect):
        """Test when extra is already a dictionary"""
        original_dict = {"key": "value"}
        mock_prospect.extra = original_dict
        
        ensure_extra_is_dict(mock_prospect)
        
        assert mock_prospect.extra == original_dict
    
    def test_ensure_extra_valid_json_string(self, mock_prospect):
        """Test when extra is a valid JSON string"""
        json_string = '{"key": "value", "number": 42}'
        mock_prospect.extra = json_string
        
        ensure_extra_is_dict(mock_prospect)
        
        assert mock_prospect.extra == {"key": "value", "number": 42}
    
    def test_ensure_extra_invalid_json_string(self, mock_prospect):
        """Test when extra is an invalid JSON string"""
        mock_prospect.extra = "invalid json string"
        
        with patch('app.services.llm_service_utils.logger') as mock_logger:
            ensure_extra_is_dict(mock_prospect)
            
            assert mock_prospect.extra == {}
            mock_logger.warning.assert_called_once()
    
    def test_ensure_extra_non_dict_type(self, mock_prospect):
        """Test when extra is neither None, string, nor dict"""
        mock_prospect.extra = 12345  # Integer
        
        with patch('app.services.llm_service_utils.logger') as mock_logger:
            ensure_extra_is_dict(mock_prospect)
            
            assert mock_prospect.extra == {}
            mock_logger.warning.assert_called_once()
    
    def test_ensure_extra_empty_string(self, mock_prospect):
        """Test when extra is an empty string"""
        mock_prospect.extra = ""
        
        ensure_extra_is_dict(mock_prospect)
        
        assert mock_prospect.extra == {}


class TestUpdateProspectTimestamps:
    """Test update_prospect_timestamps function"""
    
    @pytest.fixture
    def mock_prospect(self):
        """Create a mock prospect for testing"""
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect"
        return prospect
    
    def test_update_timestamps_success(self, mock_prospect):
        """Test successful timestamp update"""
        model_name = "qwen3:latest"
        
        update_prospect_timestamps(mock_prospect, model_name)
        
        assert mock_prospect.ollama_processed_at is not None
        assert isinstance(mock_prospect.ollama_processed_at, datetime)
        assert mock_prospect.ollama_model_version == model_name
    
    def test_update_timestamps_with_exception(self, mock_prospect):
        """Test timestamp update with exception handling"""
        model_name = "qwen3:latest"
        
        # Make setting the timestamp raise an exception
        def mock_setter(value):
            raise Exception("Database error")
        
        type(mock_prospect).ollama_processed_at = property(lambda x: None, mock_setter)
        
        with patch('app.services.llm_service_utils.logger') as mock_logger:
            update_prospect_timestamps(mock_prospect, model_name)
            
            mock_logger.error.assert_called_once()


class TestEmitFieldUpdate:
    """Test emit_field_update function"""
    
    def test_emit_field_update_with_callback(self):
        """Test emitting field update with callback"""
        prospect_id = "test-prospect-123"
        field_type = "values"
        field_data = {"estimated_value_single": 100000}
        
        mock_callback = Mock()
        
        emit_field_update(prospect_id, field_type, field_data, mock_callback)
        
        mock_callback.assert_called_once()
        call_args = mock_callback.call_args[0]
        assert call_args[0] == 'field_update'
        
        event_data = call_args[1]
        assert event_data['prospect_id'] == prospect_id
        assert event_data['field_type'] == field_type
        assert event_data['fields'] == field_data
        assert 'timestamp' in event_data
    
    def test_emit_field_update_no_callback(self):
        """Test emitting field update without callback"""
        # Should not raise any exceptions
        result = emit_field_update("prospect-123", "values", {"test": "data"})
        assert result is None
    
    def test_emit_field_update_callback_exception(self):
        """Test emitting field update when callback raises exception"""
        mock_callback = Mock()
        mock_callback.side_effect = Exception("Callback error")
        
        with patch('app.services.llm_service_utils.logger') as mock_logger:
            emit_field_update("prospect-123", "values", {"test": "data"}, mock_callback)
            
            mock_logger.error.assert_called_once()


class TestCalculateProgressPercentage:
    """Test calculate_progress_percentage function"""
    
    def test_calculate_progress_normal(self):
        """Test normal progress calculation"""
        assert calculate_progress_percentage(25, 100) == 25.0
        assert calculate_progress_percentage(0, 100) == 0.0
        assert calculate_progress_percentage(100, 100) == 100.0
    
    def test_calculate_progress_zero_total(self):
        """Test progress calculation with zero total"""
        assert calculate_progress_percentage(0, 0) == 100.0
        assert calculate_progress_percentage(5, 0) == 100.0
    
    def test_calculate_progress_negative_total(self):
        """Test progress calculation with negative total"""
        assert calculate_progress_percentage(5, -10) == 100.0
    
    def test_calculate_progress_over_hundred(self):
        """Test progress calculation that would exceed 100%"""
        assert calculate_progress_percentage(150, 100) == 100.0
    
    def test_calculate_progress_fractional(self):
        """Test progress calculation with fractional results"""
        result = calculate_progress_percentage(1, 3)
        assert abs(result - 33.333333333333336) < 0.000001  # Float precision


class TestFormatDuration:
    """Test format_duration function"""
    
    def test_format_duration_seconds(self):
        """Test formatting durations in seconds"""
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"
        assert format_duration(0) == "0s"
    
    def test_format_duration_minutes(self):
        """Test formatting durations in minutes"""
        assert format_duration(60) == "1m"
        assert format_duration(90) == "1m 30s"
        assert format_duration(120) == "2m"
        assert format_duration(3599) == "59m 59s"
    
    def test_format_duration_hours(self):
        """Test formatting durations in hours"""
        assert format_duration(3600) == "1h"
        assert format_duration(3660) == "1h 1m"
        assert format_duration(7200) == "2h"
        assert format_duration(7260) == "2h 1m"
    
    def test_format_duration_fractional_seconds(self):
        """Test formatting fractional seconds"""
        assert format_duration(30.7) == "30s"
        assert format_duration(59.9) == "59s"


class TestGetEnhancementFieldNames:
    """Test get_enhancement_field_names function"""
    
    def test_get_field_names_values(self):
        """Test getting field names for values enhancement"""
        result = get_enhancement_field_names("values")
        expected = {
            'values': ['estimated_value_single', 'estimated_value_min', 'estimated_value_max', 'estimated_value_text']
        }
        assert result == expected
    
    def test_get_field_names_naics(self):
        """Test getting field names for NAICS enhancement"""
        result = get_enhancement_field_names("naics")
        expected = {
            'naics': ['naics', 'naics_description', 'naics_source']
        }
        assert result == expected
    
    def test_get_field_names_titles(self):
        """Test getting field names for titles enhancement"""
        result = get_enhancement_field_names("titles")
        expected = {
            'titles': ['ai_enhanced_title']
        }
        assert result == expected
    
    def test_get_field_names_set_asides(self):
        """Test getting field names for set_asides enhancement"""
        result = get_enhancement_field_names("set_asides")
        expected = {
            'set_asides': ['set_aside_standardized', 'set_aside_standardized_label']
        }
        assert result == expected
    
    def test_get_field_names_all(self):
        """Test getting field names for all enhancements"""
        result = get_enhancement_field_names("all")
        
        assert 'all' in result
        all_fields = result['all']
        
        # Should contain fields from all enhancement types
        assert 'estimated_value_single' in all_fields
        assert 'naics' in all_fields
        assert 'ai_enhanced_title' in all_fields
        assert 'set_aside_standardized' in all_fields
    
    def test_get_field_names_unknown_type(self):
        """Test getting field names for unknown enhancement type"""
        result = get_enhancement_field_names("unknown_type")
        expected = {'unknown_type': []}
        assert result == expected


class TestShouldSkipProspect:
    """Test should_skip_prospect function"""
    
    @pytest.fixture
    def mock_prospect(self):
        """Create a mock prospect for testing"""
        prospect = Mock(spec=Prospect)
        prospect.estimated_value_single = None
        prospect.naics = None
        prospect.naics_source = None
        prospect.ai_enhanced_title = None
        prospect.set_aside_standardized = None
        prospect.ollama_processed_at = None
        return prospect
    
    def test_should_skip_values_already_processed(self, mock_prospect):
        """Test skipping prospect that already has parsed values"""
        mock_prospect.estimated_value_single = 100000.0
        
        result = should_skip_prospect(mock_prospect, "values", skip_existing=True)
        
        assert result is True
    
    def test_should_skip_values_not_processed(self, mock_prospect):
        """Test not skipping prospect that needs value parsing"""
        result = should_skip_prospect(mock_prospect, "values", skip_existing=True)
        
        assert result is False
    
    def test_should_skip_naics_already_inferred(self, mock_prospect):
        """Test skipping prospect that already has LLM-inferred NAICS"""
        mock_prospect.naics = "541511"
        mock_prospect.naics_source = "llm_inferred"
        
        result = should_skip_prospect(mock_prospect, "naics", skip_existing=True)
        
        assert result is True
    
    def test_should_skip_naics_original_source(self, mock_prospect):
        """Test not skipping prospect with original NAICS (can be enhanced)"""
        mock_prospect.naics = "541511"
        mock_prospect.naics_source = "original"
        
        result = should_skip_prospect(mock_prospect, "naics", skip_existing=True)
        
        assert result is False
    
    def test_should_skip_titles_already_enhanced(self, mock_prospect):
        """Test skipping prospect with enhanced title"""
        mock_prospect.ai_enhanced_title = "Enhanced Title"
        
        result = should_skip_prospect(mock_prospect, "titles", skip_existing=True)
        
        assert result is True
    
    def test_should_skip_set_asides_already_standardized(self, mock_prospect):
        """Test skipping prospect with standardized set-aside"""
        mock_prospect.set_aside_standardized = "SMALL_BUSINESS"
        
        result = should_skip_prospect(mock_prospect, "set_asides", skip_existing=True)
        
        assert result is True
    
    def test_should_skip_all_already_processed(self, mock_prospect):
        """Test skipping prospect that has been fully processed"""
        mock_prospect.ollama_processed_at = datetime.now(timezone.utc)
        
        result = should_skip_prospect(mock_prospect, "all", skip_existing=True)
        
        assert result is True
    
    def test_should_not_skip_when_skip_existing_false(self, mock_prospect):
        """Test not skipping when skip_existing is False"""
        mock_prospect.estimated_value_single = 100000.0  # Already processed
        
        result = should_skip_prospect(mock_prospect, "values", skip_existing=False)
        
        assert result is False


class TestCreateEnhancementSummary:
    """Test create_enhancement_summary function"""
    
    def test_create_summary_all_successful(self):
        """Test creating summary when all enhancements succeed"""
        results = {
            'values': True,
            'naics': True,
            'titles': True,
            'set_asides': True
        }
        
        summary = create_enhancement_summary(results)
        
        assert summary['total_attempted'] == 4
        assert summary['successful'] == 4
        assert summary['failed'] == 0
        assert summary['success_rate'] == 100.0
        assert summary['details'] == results
    
    def test_create_summary_partial_success(self):
        """Test creating summary with partial success"""
        results = {
            'values': True,
            'naics': False,
            'titles': True,
            'set_asides': False
        }
        
        summary = create_enhancement_summary(results)
        
        assert summary['total_attempted'] == 4
        assert summary['successful'] == 2
        assert summary['failed'] == 2
        assert summary['success_rate'] == 50.0
        assert summary['details'] == results
    
    def test_create_summary_all_failed(self):
        """Test creating summary when all enhancements fail"""
        results = {
            'values': False,
            'naics': False,
            'titles': False
        }
        
        summary = create_enhancement_summary(results)
        
        assert summary['total_attempted'] == 3
        assert summary['successful'] == 0
        assert summary['failed'] == 3
        assert summary['success_rate'] == 0.0
    
    def test_create_summary_empty_results(self):
        """Test creating summary with empty results"""
        results = {}
        
        summary = create_enhancement_summary(results)
        
        assert summary['total_attempted'] == 0
        assert summary['successful'] == 0
        assert summary['failed'] == 0
        assert summary['success_rate'] == 0
        assert summary['details'] == results