"""
Unit tests for BaseLLMService - Core LLM enhancement logic
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json

from app.services.base_llm_service import BaseLLMService
from app.database.models import Prospect
from app.services.set_aside_standardization import StandardSetAside


class TestBaseLLMService:
    """Test cases for BaseLLMService core functionality"""
    
    @pytest.fixture
    def service(self):
        """Create a BaseLLMService instance for testing"""
        return BaseLLMService(model_name='test-model')
    
    @pytest.fixture
    def mock_prospect(self):
        """Create a mock prospect for testing"""
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect-123"
        prospect.title = "Test Software Development Services"
        prospect.description = "Comprehensive software development and maintenance services"
        prospect.estimated_value = 100000
        prospect.estimated_value_text = "$100,000"
        prospect.estimated_value_single = None
        prospect.estimated_value_min = None
        prospect.estimated_value_max = None
        prospect.naics = None
        prospect.naics_description = None
        prospect.naics_source = None
        prospect.ai_enhanced_title = None
        prospect.set_aside = "Small Business Set-Aside"
        prospect.set_aside_standardized = None
        prospect.set_aside_standardized_label = None
        prospect.agency = "Department of Defense"
        prospect.contract_type = "Services"
        prospect.extra = {}
        return prospect


class TestParseExistingNAICS:
    """Test NAICS parsing functionality"""
    
    @pytest.fixture
    def service(self):
        return BaseLLMService()
    
    def test_parse_naics_pipe_format(self, service):
        """Test parsing NAICS in standard pipe format"""
        result = service.parse_existing_naics("334516 | Analytical Laboratory Instrument Manufacturing")
        
        assert result['code'] == '334516'
        assert result['description'] == 'Analytical Laboratory Instrument Manufacturing'
        assert result['standardized_format'] == '334516 | Analytical Laboratory Instrument Manufacturing'
        assert result['original_format'] == 'pipe'
    
    def test_parse_naics_colon_format(self, service):
        """Test parsing NAICS in HHS colon format"""
        result = service.parse_existing_naics("334516 : Analytical Laboratory Instrument Manufacturing")
        
        assert result['code'] == '334516'
        assert result['description'] == 'Analytical Laboratory Instrument Manufacturing'
        assert result['standardized_format'] == '334516 | Analytical Laboratory Instrument Manufacturing'
        assert result['original_format'] == 'colon'
    
    def test_parse_naics_hyphen_format(self, service):
        """Test parsing NAICS in hyphen format"""
        result = service.parse_existing_naics("334516 - Analytical Laboratory Instrument Manufacturing")
        
        assert result['code'] == '334516'
        assert result['description'] == 'Analytical Laboratory Instrument Manufacturing'
        assert result['standardized_format'] == '334516 | Analytical Laboratory Instrument Manufacturing'
        assert result['original_format'] == 'hyphen'
    
    def test_parse_naics_space_format(self, service):
        """Test parsing NAICS in space-separated format"""
        result = service.parse_existing_naics("334516 Analytical Laboratory Instrument Manufacturing")
        
        assert result['code'] == '334516'
        assert result['description'] == 'Analytical Laboratory Instrument Manufacturing'
        assert result['standardized_format'] == '334516 | Analytical Laboratory Instrument Manufacturing'
        assert result['original_format'] == 'space'
    
    def test_parse_naics_code_only(self, service):
        """Test parsing NAICS code without description"""
        with patch('app.services.base_llm_service.get_naics_description') as mock_desc:
            mock_desc.return_value = 'Mock Description'
            result = service.parse_existing_naics("334516")
            
            assert result['code'] == '334516'
            assert result['description'] == 'Mock Description'
            assert result['standardized_format'] == '334516 | Mock Description'
            assert result['original_format'] == 'code_only'
    
    def test_parse_naics_decimal_format(self, service):
        """Test parsing NAICS with decimal point (DOT/SSA format)"""
        result = service.parse_existing_naics("334516.0")
        
        assert result['code'] == '334516'
        # Should call get_naics_description for the description
    
    def test_parse_naics_tbd_values(self, service):
        """Test parsing TBD placeholder values"""
        tbd_values = ['TBD', 'TO BE DETERMINED', 'N/A', 'NA']
        
        for tbd_value in tbd_values:
            result = service.parse_existing_naics(tbd_value)
            assert result['code'] is None
            assert result['description'] is None
            assert result['standardized_format'] is None
    
    def test_parse_naics_none_empty(self, service):
        """Test parsing None and empty values"""
        assert service.parse_existing_naics(None)['code'] is None
        assert service.parse_existing_naics("")['code'] is None
        assert service.parse_existing_naics("   ")['code'] is None


class TestExtractNAICSFromExtra:
    """Test NAICS extraction from extra field JSON data"""
    
    @pytest.fixture
    def service(self):
        return BaseLLMService()
    
    def test_extract_acquisition_gateway_pattern(self, service):
        """Test extracting NAICS from Acquisition Gateway format"""
        extra_data = {"naics_code": "236220"}
        
        result = service.extract_naics_from_extra_field(extra_data)
        
        assert result['code'] == '236220'
        assert result['found_in_extra'] is True
    
    def test_extract_hhs_pattern(self, service):
        """Test extracting NAICS from HHS format"""
        extra_data = {"primary_naics": "334516 : Analytical Laboratory Instrument Manufacturing"}
        
        with patch.object(service, 'parse_existing_naics') as mock_parse:
            mock_parse.return_value = {'code': '334516', 'description': 'Test Description'}
            result = service.extract_naics_from_extra_field(extra_data)
            
            assert result['code'] == '334516'
            assert result['description'] == 'Test Description'
            assert result['found_in_extra'] is True
    
    def test_extract_fallback_search(self, service):
        """Test fallback search for NAICS in various fields"""
        extra_data = {"industry_code": "334516"}
        
        with patch.object(service, 'parse_existing_naics') as mock_parse:
            mock_parse.return_value = {'code': '334516', 'description': 'Test Description'}
            result = service.extract_naics_from_extra_field(extra_data)
            
            assert result['code'] == '334516'
            assert result['found_in_extra'] is True
    
    def test_extract_json_string_input(self, service):
        """Test extracting from JSON string input"""
        extra_data_str = '{"naics_code": "236220"}'
        
        result = service.extract_naics_from_extra_field(extra_data_str)
        
        assert result['code'] == '236220'
        assert result['found_in_extra'] is True
    
    def test_extract_invalid_json_string(self, service):
        """Test handling invalid JSON string"""
        result = service.extract_naics_from_extra_field("invalid json")
        
        assert result['code'] is None
        assert result['found_in_extra'] is False
    
    def test_extract_skip_tbd_values(self, service):
        """Test skipping TBD values during extraction"""
        extra_data = {"primary_naics": "TBD"}
        
        result = service.extract_naics_from_extra_field(extra_data)
        
        assert result['code'] is None
        assert result['found_in_extra'] is False
    
    def test_extract_six_digit_number_search(self, service):
        """Test last resort 6-digit number search"""
        extra_data = {"description": "This project involves 334516 manufacturing work"}
        
        with patch.object(service, 'parse_existing_naics') as mock_parse:
            mock_parse.return_value = {'code': '334516', 'description': 'Test Description'}
            result = service.extract_naics_from_extra_field(extra_data)
            
            assert result['code'] == '334516'
            assert result['found_in_extra'] is True


class TestLLMOutputLogging:
    """Test LLM output logging functionality"""
    
    @pytest.fixture
    def service(self):
        return BaseLLMService()
    
    @patch('app.services.base_llm_service.db.session')
    @patch('app.services.base_llm_service.LLMOutput')
    def test_log_llm_output_success(self, mock_llm_output, mock_db_session, service):
        """Test successful LLM output logging"""
        service._log_llm_output(
            prospect_id="test-123",
            enhancement_type="naics_classification",
            prompt="Test prompt",
            response="Test response",
            parsed_result={"code": "334516"},
            success=True,
            processing_time=1.5
        )
        
        mock_llm_output.assert_called_once()
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @patch('app.services.base_llm_service.db.session')
    @patch('app.services.base_llm_service.logger')
    def test_log_llm_output_failure(self, mock_logger, mock_db_session, service):
        """Test LLM output logging failure handling"""
        mock_db_session.add.side_effect = Exception("Database error")
        
        service._log_llm_output(
            prospect_id="test-123",
            enhancement_type="naics_classification",
            prompt="Test prompt",
            response="Test response",
            parsed_result={"code": "334516"},
            success=True
        )
        
        mock_logger.error.assert_called_once()
        mock_db_session.rollback.assert_called_once()


class TestLLMEnhancementMethods:
    """Test core LLM enhancement methods (mocked to avoid actual LLM calls)"""
    
    @pytest.fixture
    def service(self):
        return BaseLLMService()
    
    @patch('app.services.base_llm_service.call_ollama')
    @patch('app.services.base_llm_service.get_naics_description')
    @patch('app.services.base_llm_service.validate_naics_code')
    def test_classify_naics_with_llm_success(self, mock_validate, mock_get_desc, mock_ollama, service):
        """Test successful NAICS classification"""
        # Setup mocks
        mock_ollama.return_value = '{"code": "334516", "confidence": 0.9}'
        mock_validate.return_value = True
        mock_get_desc.return_value = "Test Description"
        
        result = service.classify_naics_with_llm("Software Development", "Custom software services")
        
        assert result['code'] == '334516'
        assert result['description'] == "Test Description"
        assert result['confidence'] == 0.9
    
    @patch('app.services.base_llm_service.call_ollama')
    def test_classify_naics_with_llm_json_error(self, mock_ollama, service):
        """Test NAICS classification with JSON parsing error"""
        mock_ollama.return_value = "invalid json"
        
        result = service.classify_naics_with_llm("Software Development", "Custom software services")
        
        assert result['code'] is None
        assert result['confidence'] == 0.0
    
    @patch('app.services.base_llm_service.call_ollama')
    def test_parse_contract_value_with_llm_success(self, mock_ollama, service):
        """Test successful contract value parsing"""
        mock_ollama.return_value = '{"single": 100000, "min": null, "max": null, "confidence": 0.95}'
        
        result = service.parse_contract_value_with_llm("$100,000")
        
        assert result['single'] == 100000.0
        assert result['min'] is None
        assert result['max'] is None
        assert result['confidence'] == 0.95
    
    @patch('app.services.base_llm_service.call_ollama')
    def test_parse_contract_value_with_llm_range(self, mock_ollama, service):
        """Test contract value parsing for ranges"""
        mock_ollama.return_value = '{"single": null, "min": 50000, "max": 150000, "confidence": 0.85}'
        
        result = service.parse_contract_value_with_llm("$50K - $150K")
        
        assert result['single'] is None
        assert result['min'] == 50000.0
        assert result['max'] == 150000.0
        assert result['confidence'] == 0.85
    
    @patch('app.services.base_llm_service.call_ollama')
    def test_enhance_title_with_llm_success(self, mock_ollama, service):
        """Test successful title enhancement"""
        mock_ollama.return_value = '{"enhanced_title": "Professional Software Development Services", "confidence": 0.9, "reasoning": "Made more professional"}'
        
        result = service.enhance_title_with_llm("Software Dev", "Custom software development")
        
        assert result['enhanced_title'] == "Professional Software Development Services"
        assert result['confidence'] == 0.9
        assert result['reasoning'] == "Made more professional"
    
    @patch('app.services.base_llm_service.call_ollama')
    def test_enhance_title_with_llm_no_enhancement(self, mock_ollama, service):
        """Test title enhancement when no improvement is made"""
        mock_ollama.return_value = '{"enhanced_title": "", "confidence": 0.1}'
        
        result = service.enhance_title_with_llm("Good Title", "Description")
        
        assert result['enhanced_title'] is None
        assert result['confidence'] == 0.0
    
    def test_standardize_set_aside_with_llm(self, service):
        """Test set-aside standardization"""
        with patch.object(service.set_aside_standardizer, 'standardize') as mock_standardize:
            mock_result = StandardSetAside.SMALL_BUSINESS
            mock_standardize.return_value = mock_result
            
            result = service.standardize_set_aside_with_llm("Small Business Set-Aside")
            
            assert result == mock_result
            mock_standardize.assert_called_once_with("Small Business Set-Aside")


class TestProcessSingleProspectEnhancement:
    """Test the main single prospect enhancement method"""
    
    @pytest.fixture
    def service(self):
        return BaseLLMService()
    
    @pytest.fixture
    def mock_prospect(self):
        """Create a comprehensive mock prospect"""
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect-123"
        prospect.title = "Software Development"
        prospect.description = "Custom software development services"
        prospect.estimated_value_text = "$100,000"
        prospect.estimated_value = 100000
        prospect.estimated_value_single = None
        prospect.estimated_value_min = None
        prospect.estimated_value_max = None
        prospect.naics = None
        prospect.naics_description = None
        prospect.naics_source = None
        prospect.ai_enhanced_title = None
        prospect.set_aside = "Small Business"
        prospect.set_aside_standardized = None
        prospect.set_aside_standardized_label = None
        prospect.agency = "DOD"
        prospect.contract_type = "Services"
        prospect.extra = {}
        return prospect
    
    @patch('app.services.llm_service_utils.ensure_extra_is_dict')
    @patch('app.services.llm_service_utils.update_prospect_timestamps')
    def test_process_single_prospect_all_enhancements(self, mock_update_timestamps, mock_ensure_dict, service, mock_prospect):
        """Test processing all enhancement types for a single prospect"""
        # Mock the LLM methods
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value, \
             patch.object(service, 'extract_naics_from_extra_field') as mock_extract_naics, \
             patch.object(service, 'classify_naics_with_llm') as mock_classify_naics, \
             patch.object(service, 'enhance_title_with_llm') as mock_enhance_title, \
             patch.object(service, 'standardize_set_aside_with_llm') as mock_standardize_set_aside:
            
            # Setup mock returns
            mock_parse_value.return_value = {'single': 100000.0, 'min': None, 'max': None}
            mock_extract_naics.return_value = {'found_in_extra': False, 'code': None}
            mock_classify_naics.return_value = {'code': '541511', 'description': 'Custom Computer Programming Services'}
            mock_enhance_title.return_value = {'enhanced_title': 'Professional Software Development Services'}
            mock_standardize_set_aside.return_value = StandardSetAside.SMALL_BUSINESS
            
            # Test the enhancement
            results = service.process_single_prospect_enhancement(mock_prospect, "all")
            
            # Verify results
            assert results['values'] is True
            assert results['naics'] is True
            assert results['titles'] is True
            assert results['set_asides'] is True
            
            # Verify prospect was updated
            assert mock_prospect.estimated_value_single == 100000.0
            assert mock_prospect.naics == '541511'
            assert mock_prospect.naics_description == 'Custom Computer Programming Services'
            assert mock_prospect.ai_enhanced_title == 'Professional Software Development Services'
            assert mock_prospect.set_aside_standardized == StandardSetAside.SMALL_BUSINESS.code
    
    def test_process_single_prospect_specific_enhancement(self, service, mock_prospect):
        """Test processing only specific enhancement type"""
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value:
            mock_parse_value.return_value = {'single': 100000.0, 'min': None, 'max': None}
            
            results = service.process_single_prospect_enhancement(mock_prospect, "values")
            
            assert results['values'] is True
            assert results['naics'] is False
            assert results['titles'] is False
            assert results['set_asides'] is False
    
    def test_process_with_progress_callback(self, service, mock_prospect):
        """Test processing with progress callback"""
        callback_calls = []
        
        def progress_callback(update):
            callback_calls.append(update)
        
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value:
            mock_parse_value.return_value = {'single': 100000.0, 'min': None, 'max': None}
            
            service.process_single_prospect_enhancement(
                mock_prospect, 
                "values", 
                progress_callback=progress_callback
            )
            
            # Verify callback was called
            assert len(callback_calls) > 0
            assert callback_calls[0]['field'] == 'values'
            assert callback_calls[0]['prospect_id'] == mock_prospect.id