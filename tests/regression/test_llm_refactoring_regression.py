"""
Regression tests for LLM service refactoring

These tests ensure that the refactored services produce identical or better results
compared to the original implementation.
"""

import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime, timezone

from app.services.base_llm_service import BaseLLMService
from app.services.contract_llm_service import ContractLLMService
from app.services.iterative_llm_service import IterativeLLMService
from app.database.models import Prospect


class TestNAICSParsingRegression:
    """Test that NAICS parsing behavior is preserved after refactoring"""
    
    @pytest.fixture
    def service(self):
        return BaseLLMService()
    
    def test_naics_parsing_formats_preserved(self, service):
        """Test that all NAICS format parsing still works as before"""
        # Test cases that should work the same as before refactoring
        test_cases = [
            ("334516 | Analytical Laboratory Instrument Manufacturing", "334516", "Analytical Laboratory Instrument Manufacturing", "pipe"),
            ("334516 : Analytical Laboratory Instrument Manufacturing", "334516", "Analytical Laboratory Instrument Manufacturing", "colon"),
            ("334516 - Analytical Laboratory Instrument Manufacturing", "334516", "Analytical Laboratory Instrument Manufacturing", "hyphen"),
            ("334516 Analytical Laboratory Instrument Manufacturing", "334516", "Analytical Laboratory Instrument Manufacturing", "space"),
            ("334516", "334516", None, "code_only"),  # Description comes from lookup
            ("334516.0", "334516", None, None),  # Decimal format, description from lookup
            ("TBD", None, None, None),
            ("TO BE DETERMINED", None, None, None),
            ("N/A", None, None, None),
            (None, None, None, None),
            ("", None, None, None)
        ]
        
        for input_value, expected_code, expected_desc, expected_format in test_cases:
            with patch('app.services.base_llm_service.get_naics_description') as mock_get_desc:
                # Mock description lookup for code-only cases
                if expected_desc is None and expected_code:
                    mock_get_desc.return_value = "Mocked Description"
                    expected_desc = "Mocked Description"
                
                result = service.parse_existing_naics(input_value)
                
                assert result['code'] == expected_code, f"Failed for input: {input_value}"
                if expected_desc:
                    assert result['description'] == expected_desc, f"Failed for input: {input_value}"
                if expected_format:
                    assert result['original_format'] == expected_format, f"Failed for input: {input_value}"
    
    def test_naics_extraction_from_extra_preserved(self, service):
        """Test that NAICS extraction from extra field works as before"""
        test_cases = [
            # Acquisition Gateway format
            ({"naics_code": "236220"}, "236220", None, True),
            
            # HHS format
            ({"primary_naics": "334516 : Analytical Laboratory Instrument Manufacturing"}, "334516", None, True),
            
            # TBD handling
            ({"primary_naics": "TBD"}, None, None, False),
            
            # Fallback search
            ({"industry_code": "541511"}, "541511", None, True),
            
            # JSON string input
            ('{"naics_code": "236220"}', "236220", None, True),
            
            # Invalid cases
            ("invalid json", None, None, False),
            (None, None, None, False),
            ({}, None, None, False),
        ]
        
        for extra_input, expected_code, expected_desc, expected_found in test_cases:
            with patch.object(service, 'parse_existing_naics') as mock_parse:
                if expected_code:
                    mock_parse.return_value = {'code': expected_code, 'description': expected_desc}
                
                result = service.extract_naics_from_extra_field(extra_input)
                
                assert result['code'] == expected_code, f"Failed for input: {extra_input}"
                assert result['found_in_extra'] == expected_found, f"Failed for input: {extra_input}"


class TestValueParsingRegression:
    """Test that value parsing behavior is preserved"""
    
    @pytest.fixture
    def service(self):
        return BaseLLMService()
    
    @patch('app.services.base_llm_service.call_ollama')
    def test_value_parsing_response_formats(self, mock_ollama, service):
        """Test that value parsing handles all response formats correctly"""
        test_cases = [
            # Single value
            ('{"single": 100000, "min": null, "max": null, "confidence": 0.9}', 100000.0, None, None),
            
            # Range value
            ('{"single": null, "min": 50000, "max": 150000, "confidence": 0.85}', None, 50000.0, 150000.0),
            
            # Both single and range (should prefer range logic in original implementation)
            ('{"single": 100000, "min": 50000, "max": 150000, "confidence": 0.9}', None, 50000.0, 150000.0),
            
            # Invalid negative values (should be filtered out)
            ('{"single": -100000, "min": null, "max": null, "confidence": 0.9}', None, None, None),
            
            # Invalid JSON
            ('invalid json response', None, None, None),
        ]
        
        for mock_response, expected_single, expected_min, expected_max in test_cases:
            mock_ollama.return_value = mock_response
            
            result = service.parse_contract_value_with_llm("$100,000")
            
            assert result['single'] == expected_single, f"Single value failed for: {mock_response}"
            assert result['min'] == expected_min, f"Min value failed for: {mock_response}"
            assert result['max'] == expected_max, f"Max value failed for: {mock_response}"


class TestTitleEnhancementRegression:
    """Test that title enhancement behavior is preserved"""
    
    @pytest.fixture
    def service(self):
        return BaseLLMService()
    
    @patch('app.services.base_llm_service.call_ollama')
    def test_title_enhancement_response_handling(self, mock_ollama, service):
        """Test that title enhancement response handling is preserved"""
        test_cases = [
            # Successful enhancement
            ('{"enhanced_title": "Professional Software Development Services", "confidence": 0.9, "reasoning": "Made more professional"}',
             "Professional Software Development Services", 0.9, "Made more professional"),
            
            # No enhancement (empty title)
            ('{"enhanced_title": "", "confidence": 0.1, "reasoning": "No improvement needed"}',
             None, 0.0, "No improvement needed"),
            
            # Same as original (no enhancement)
            ('{"enhanced_title": "Original Title", "confidence": 0.5}',
             None, 0.0, ""),  # When same as original, should return None
            
            # Invalid JSON
            ('invalid json response', None, 0.0, ''),
        ]
        
        for mock_response, expected_title, expected_confidence, expected_reasoning in test_cases:
            mock_ollama.return_value = mock_response
            
            original_title = "Original Title"
            result = service.enhance_title_with_llm(original_title, "Description", "Agency")
            
            assert result['enhanced_title'] == expected_title, f"Title failed for: {mock_response}"
            assert result['confidence'] == expected_confidence, f"Confidence failed for: {mock_response}"
            if expected_reasoning:
                assert result['reasoning'] == expected_reasoning, f"Reasoning failed for: {mock_response}"


class TestBatchProcessingRegression:
    """Test that batch processing behavior is preserved"""
    
    @pytest.fixture
    def service(self):
        return ContractLLMService()
    
    @pytest.fixture
    def sample_prospects(self):
        """Create sample prospects for batch testing"""
        prospects = []
        for i in range(3):
            prospect = Mock(spec=Prospect)
            prospect.id = f"regression-prospect-{i}"
            prospect.title = f"Test Title {i}"
            prospect.description = f"Test Description {i}"
            prospect.estimated_value_text = f"${(i+1)*50000}"
            prospect.estimated_value_single = None
            prospect.naics = None
            prospect.ai_enhanced_title = None
            prospect.set_aside = "Small Business"
            prospect.set_aside_standardized = None
            prospect.extra = {}
            prospect.ollama_processed_at = None
            prospect.ollama_model_version = None
            prospects.append(prospect)
        return prospects
    
    @patch('app.services.contract_llm_service.db.session')
    def test_batch_processing_counts_preserved(self, mock_db_session, service, sample_prospects):
        """Test that batch processing returns correct counts"""
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value:
            # Mock successful processing for all prospects
            mock_parse_value.return_value = {'single': 100000, 'min': None, 'max': None}
            
            processed_count = service.enhance_prospect_values(sample_prospects)
            
            # Should process all prospects that need processing
            assert processed_count == len(sample_prospects)
    
    @patch('app.services.contract_llm_service.db.session')
    def test_batch_processing_skips_existing(self, mock_db_session, service, sample_prospects):
        """Test that batch processing correctly skips already processed prospects"""
        # Mark one prospect as already processed
        sample_prospects[1].estimated_value_single = 75000.0
        
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value:
            mock_parse_value.return_value = {'single': 100000, 'min': None, 'max': None}
            
            processed_count = service.enhance_prospect_values(sample_prospects)
            
            # Should process 2 out of 3 prospects (skipping the pre-processed one)
            assert processed_count == 2


class TestIterativeProcessingRegression:
    """Test that iterative processing behavior is preserved"""
    
    @pytest.fixture
    def service(self):
        return IterativeLLMService()
    
    def test_filter_building_logic_preserved(self, service):
        """Test that filter building logic works as before"""
        # Test different enhancement types
        enhancement_types = ["values", "naics", "titles", "set_asides", "all"]
        
        for enhancement_type in enhancement_types:
            # Should return a valid filter condition
            filter_condition = service._build_enhancement_filter(enhancement_type, skip_existing=True)
            assert filter_condition is not None, f"Filter failed for {enhancement_type}"
            
            # Should also work without skip_existing
            filter_condition_no_skip = service._build_enhancement_filter(enhancement_type, skip_existing=False)
            assert filter_condition_no_skip is not None, f"No-skip filter failed for {enhancement_type}"
    
    def test_progress_tracking_structure_preserved(self, service):
        """Test that progress tracking structure is preserved"""
        progress = service.get_progress()
        
        # Should have all expected fields
        expected_fields = ["status", "current_type", "processed", "total", "current_prospect", "started_at", "errors"]
        
        for field in expected_fields:
            assert field in progress, f"Missing progress field: {field}"
        
        # Initial state should be correct
        assert progress["status"] == "idle"
        assert progress["processed"] == 0
        assert progress["total"] == 0


class TestSingleProspectEnhancementRegression:
    """Test that single prospect enhancement produces correct results"""
    
    @pytest.fixture
    def service(self):
        return BaseLLMService()
    
    @pytest.fixture
    def comprehensive_prospect(self):
        """Create a prospect that needs all types of enhancement"""
        prospect = Mock(spec=Prospect)
        prospect.id = "comprehensive-prospect"
        prospect.title = "Software Dev"
        prospect.description = "Custom software development services"
        prospect.estimated_value_text = "$100,000 - $200,000"
        prospect.estimated_value = None
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
        prospect.agency = "DOD"
        prospect.contract_type = "Services"
        prospect.extra = {}
        return prospect
    
    def test_comprehensive_enhancement_results(self, service, comprehensive_prospect):
        """Test that comprehensive enhancement returns expected results structure"""
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value, \
             patch.object(service, 'extract_naics_from_extra_field') as mock_extract_naics, \
             patch.object(service, 'classify_naics_with_llm') as mock_classify_naics, \
             patch.object(service, 'enhance_title_with_llm') as mock_enhance_title, \
             patch.object(service, 'standardize_set_aside_with_llm') as mock_standardize_set_aside, \
             patch('app.services.llm_service_utils.ensure_extra_is_dict'), \
             patch('app.services.llm_service_utils.update_prospect_timestamps'):
            
            # Setup successful mocks
            mock_parse_value.return_value = {'single': None, 'min': 100000, 'max': 200000}
            mock_extract_naics.return_value = {'found_in_extra': False, 'code': None}
            mock_classify_naics.return_value = {'code': '541511', 'description': 'Custom Computer Programming Services'}
            mock_enhance_title.return_value = {'enhanced_title': 'Professional Software Development Services'}
            
            from app.services.set_aside_standardization import StandardSetAside
            mock_standardize_set_aside.return_value = StandardSetAside.SMALL_BUSINESS
            
            results = service.process_single_prospect_enhancement(comprehensive_prospect, "all")
            
            # Should return results for all enhancement types
            expected_keys = ['values', 'naics', 'titles', 'set_asides']
            for key in expected_keys:
                assert key in results, f"Missing result key: {key}"
                assert isinstance(results[key], bool), f"Result {key} should be boolean"
            
            # All should be successful in this test case
            assert all(results.values()), "All enhancements should be successful"
    
    def test_selective_enhancement_results(self, service, comprehensive_prospect):
        """Test that selective enhancement only processes requested types"""
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value, \
             patch('app.services.llm_service_utils.ensure_extra_is_dict'), \
             patch('app.services.llm_service_utils.update_prospect_timestamps'):
            
            mock_parse_value.return_value = {'single': 150000, 'min': None, 'max': None}
            
            # Test values-only enhancement
            results = service.process_single_prospect_enhancement(comprehensive_prospect, "values")
            
            # Should process values, skip others
            assert results['values'] is True
            assert results['naics'] is False
            assert results['titles'] is False
            assert results['set_asides'] is False


class TestBackwardCompatibility:
    """Test that existing APIs and interfaces are preserved"""
    
    def test_contract_service_method_signatures(self):
        """Test that ContractLLMService method signatures are preserved"""
        service = ContractLLMService()
        
        # Test that batch methods exist with expected signatures
        batch_methods = [
            'enhance_prospect_values',
            'enhance_prospect_titles', 
            'enhance_prospect_naics',
            'enhance_prospect_set_asides'
        ]
        
        for method_name in batch_methods:
            method = getattr(service, method_name)
            assert callable(method), f"{method_name} should be callable"
            
            # Should accept prospects list as first parameter
            import inspect
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            assert 'prospects' in params, f"{method_name} should accept prospects parameter"
    
    def test_iterative_service_interface_preserved(self):
        """Test that IterativeLLMService interface is preserved"""
        service = IterativeLLMService()
        
        # Should have expected methods
        expected_methods = [
            'start_enhancement',
            'stop_enhancement',
            'get_progress',
            'is_processing',
            'set_queue_service'
        ]
        
        for method_name in expected_methods:
            assert hasattr(service, method_name), f"Missing method: {method_name}"
            assert callable(getattr(service, method_name)), f"{method_name} should be callable"
    
    def test_base_service_provides_core_methods(self):
        """Test that BaseLLMService provides all expected core methods"""
        service = BaseLLMService()
        
        # Should have all core LLM methods
        core_methods = [
            'parse_existing_naics',
            'extract_naics_from_extra_field',
            'classify_naics_with_llm',
            'parse_contract_value_with_llm',
            'enhance_title_with_llm',
            'standardize_set_aside_with_llm',
            'process_single_prospect_enhancement'
        ]
        
        for method_name in core_methods:
            assert hasattr(service, method_name), f"Missing core method: {method_name}"
            assert callable(getattr(service, method_name)), f"{method_name} should be callable"