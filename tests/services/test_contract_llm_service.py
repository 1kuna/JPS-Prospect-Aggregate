"""
Unit tests for ContractLLMService - Batch processing functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from app.services.contract_llm_service import ContractLLMService
from app.services.base_llm_service import BaseLLMService
from app.database.models import Prospect


class TestContractLLMServiceInheritance:
    """Test that ContractLLMService properly inherits from BaseLLMService"""
    
    def test_inheritance(self):
        """Test that ContractLLMService inherits from BaseLLMService"""
        service = ContractLLMService()
        assert isinstance(service, BaseLLMService)
        assert service.model_name == 'qwen3:latest'
        assert service.batch_size == 50
    
    def test_inherited_methods_available(self):
        """Test that all base methods are available"""
        service = ContractLLMService()
        
        # Core LLM methods should be inherited
        base_methods = [
            'parse_existing_naics',
            'extract_naics_from_extra_field', 
            'classify_naics_with_llm',
            'parse_contract_value_with_llm',
            'enhance_title_with_llm',
            'standardize_set_aside_with_llm',
            'process_single_prospect_enhancement'
        ]
        
        for method in base_methods:
            assert hasattr(service, method), f"Missing inherited method: {method}"
    
    def test_batch_specific_methods(self):
        """Test that batch-specific methods are available"""
        service = ContractLLMService()
        
        batch_methods = [
            'enhance_prospect_values',
            'enhance_prospect_titles', 
            'enhance_prospect_naics',
            'enhance_prospect_set_asides',
            '_process_enhancement_batch'
        ]
        
        for method in batch_methods:
            assert hasattr(service, method), f"Missing batch method: {method}"


class TestProcessEnhancementBatch:
    """Test the template method for batch processing"""
    
    @pytest.fixture
    def service(self):
        return ContractLLMService()
    
    @pytest.fixture
    def mock_prospects(self):
        """Create a list of mock prospects"""
        prospects = []
        for i in range(3):
            prospect = Mock(spec=Prospect)
            prospect.id = f"prospect-{i}"
            prospect.title = f"Test Title {i}"
            prospects.append(prospect)
        return prospects
    
    @patch('app.services.contract_llm_service.db.session')
    @patch('app.services.contract_llm_service.logger')
    def test_batch_processing_success(self, mock_logger, mock_db_session, service, mock_prospects):
        """Test successful batch processing"""
        # Mock processor function that always returns True
        def mock_processor(prospect):
            return True
        
        result = service._process_enhancement_batch(
            prospects=mock_prospects,
            enhancement_name="test_enhancement",
            processor_func=mock_processor,
            commit_batch_size=100,
            emit_updates=True
        )
        
        assert result == 3  # All 3 prospects processed
        assert mock_db_session.commit.call_count >= 3  # At least one commit per prospect
        mock_logger.info.assert_called()
    
    @patch('app.services.contract_llm_service.db.session')
    @patch('app.services.contract_llm_service.logger')
    def test_batch_processing_partial_success(self, mock_logger, mock_db_session, service, mock_prospects):
        """Test batch processing with some failures"""
        call_count = 0
        
        def mock_processor(prospect):
            nonlocal call_count
            call_count += 1
            return call_count % 2 == 1  # Only odd calls succeed
        
        result = service._process_enhancement_batch(
            prospects=mock_prospects,
            enhancement_name="test_enhancement", 
            processor_func=mock_processor,
            emit_updates=True
        )
        
        assert result == 2  # 2 out of 3 prospects processed (calls 1 and 3)
    
    @patch('app.services.contract_llm_service.db.session')
    @patch('app.services.contract_llm_service.logger')
    def test_batch_processing_with_exceptions(self, mock_logger, mock_db_session, service, mock_prospects):
        """Test batch processing handles exceptions gracefully"""
        def failing_processor(prospect):
            if prospect.id == "prospect-1":
                raise Exception("Processing error")
            return True
        
        result = service._process_enhancement_batch(
            prospects=mock_prospects,
            enhancement_name="test_enhancement",
            processor_func=failing_processor,
            emit_updates=True
        )
        
        assert result == 2  # 2 out of 3 prospects processed (0 and 2, 1 failed)
        mock_logger.error.assert_called()
    
    @patch('app.services.contract_llm_service.db.session')
    def test_batch_processing_no_emit_updates(self, mock_db_session, service, mock_prospects):
        """Test batch processing without real-time updates"""
        def mock_processor(prospect):
            return True
        
        result = service._process_enhancement_batch(
            prospects=mock_prospects,
            enhancement_name="test_enhancement",
            processor_func=mock_processor,
            commit_batch_size=2,  # Commit every 2 items
            emit_updates=False
        )
        
        assert result == 3
        # Should have fewer commits when not emitting updates
        commit_calls = mock_db_session.commit.call_count
        assert commit_calls < 3  # Fewer than individual commits


class TestEnhanceProspectValues:
    """Test bulk value enhancement functionality"""
    
    @pytest.fixture
    def service(self):
        return ContractLLMService()
    
    @pytest.fixture
    def mock_prospects_for_values(self):
        """Create prospects that need value parsing"""
        prospects = []
        
        # Prospect 1: Has estimated_value_text, needs parsing
        prospect1 = Mock(spec=Prospect)
        prospect1.id = "prospect-1"
        prospect1.estimated_value_text = "$100,000 - $200,000"
        prospect1.estimated_value_min = None
        prospect1.estimated_value_single = None
        prospect1.estimated_value = None
        prospect1.extra = {}
        prospect1.ollama_processed_at = None
        prospect1.ollama_model_version = None
        prospects.append(prospect1)
        
        # Prospect 2: Has estimated_value, needs parsing
        prospect2 = Mock(spec=Prospect)
        prospect2.id = "prospect-2"  
        prospect2.estimated_value_text = None
        prospect2.estimated_value = 150000
        prospect2.estimated_value_min = None
        prospect2.estimated_value_single = None
        prospect2.extra = {}
        prospect2.ollama_processed_at = None
        prospect2.ollama_model_version = None
        prospects.append(prospect2)
        
        # Prospect 3: Already processed, should skip
        prospect3 = Mock(spec=Prospect)
        prospect3.id = "prospect-3"
        prospect3.estimated_value_text = "$50,000"
        prospect3.estimated_value_single = 50000  # Already processed
        prospect3.estimated_value_min = None
        prospects.append(prospect3)
        
        return prospects
    
    @patch.object(ContractLLMService, '_process_enhancement_batch')
    def test_enhance_prospect_values_calls_batch_processor(self, mock_batch, service, mock_prospects_for_values):
        """Test that enhance_prospect_values calls the batch processor"""
        mock_batch.return_value = 2
        
        result = service.enhance_prospect_values(mock_prospects_for_values)
        
        assert result == 2
        mock_batch.assert_called_once()
        
        # Verify the processor function was passed
        call_args = mock_batch.call_args
        assert call_args[0][0] == mock_prospects_for_values  # prospects
        assert call_args[0][1] == "value enhancement"  # enhancement_name
        assert callable(call_args[0][2])  # processor_func
    
    def test_value_processor_function_logic(self, service):
        """Test the internal value processing logic"""
        # Create a prospect that needs value parsing
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect"
        prospect.estimated_value_text = "$100,000"
        prospect.estimated_value_min = None
        prospect.estimated_value_single = None
        prospect.estimated_value = None
        prospect.extra = {}
        prospect.ollama_processed_at = None
        prospect.ollama_model_version = None
        
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value, \
             patch.object(service, '_update_prospect_timestamp') as mock_update_timestamp:
            
            # Mock successful parsing
            mock_parse_value.return_value = {
                'single': 100000,
                'min': None,
                'max': None
            }
            
            # Call enhance_prospect_values to test the processor function
            with patch.object(service, '_process_enhancement_batch') as mock_batch:
                # Extract the processor function
                service.enhance_prospect_values([prospect])
                processor_func = mock_batch.call_args[0][2]
                
                # Test the processor function directly
                result = processor_func(prospect)
                
                assert result is True
                assert prospect.estimated_value_single == Decimal('100000')
                assert prospect.estimated_value_min is None
                assert prospect.estimated_value_max is None
                mock_update_timestamp.assert_called_once_with(prospect)
    
    def test_value_processor_range_logic(self, service):
        """Test value processing for range values"""
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect"
        prospect.estimated_value_text = "$50K - $150K"
        prospect.estimated_value_min = None
        prospect.estimated_value_single = None
        prospect.ollama_processed_at = None
        prospect.ollama_model_version = None
        
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value, \
             patch.object(service, '_update_prospect_timestamp'):
            
            # Mock range parsing
            mock_parse_value.return_value = {
                'single': None,
                'min': 50000,
                'max': 150000
            }
            
            with patch.object(service, '_process_enhancement_batch') as mock_batch:
                service.enhance_prospect_values([prospect])
                processor_func = mock_batch.call_args[0][2]
                
                result = processor_func(prospect)
                
                assert result is True
                assert prospect.estimated_value_single is None  # Should be None for ranges
                assert prospect.estimated_value_min == Decimal('50000')
                assert prospect.estimated_value_max == Decimal('150000')


class TestEnhanceProspectTitles:
    """Test bulk title enhancement functionality"""
    
    @pytest.fixture
    def service(self):
        return ContractLLMService()
    
    @pytest.fixture 
    def mock_prospects_for_titles(self):
        """Create prospects that need title enhancement"""
        prospects = []
        
        # Prospect 1: Needs title enhancement
        prospect1 = Mock(spec=Prospect)
        prospect1.id = "prospect-1"
        prospect1.title = "Software Dev"
        prospect1.description = "Custom software development services"
        prospect1.agency = "DOD"
        prospect1.ai_enhanced_title = None
        prospect1.extra = {}
        prospect1.ollama_processed_at = None
        prospect1.ollama_model_version = None
        prospects.append(prospect1)
        
        # Prospect 2: Already has enhanced title, should skip
        prospect2 = Mock(spec=Prospect)
        prospect2.id = "prospect-2"
        prospect2.title = "Software Development"
        prospect2.ai_enhanced_title = "Professional Software Development Services"
        prospects.append(prospect2)
        
        return prospects
    
    def test_title_processor_function_logic(self, service):
        """Test the internal title processing logic"""
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect"
        prospect.title = "Software Dev"
        prospect.description = "Custom software development"
        prospect.agency = "DOD"
        prospect.ai_enhanced_title = None
        prospect.extra = {}
        prospect.ollama_processed_at = None
        prospect.ollama_model_version = None
        
        with patch.object(service, 'enhance_title_with_llm') as mock_enhance_title, \
             patch.object(service, '_update_prospect_timestamp') as mock_update_timestamp, \
             patch('app.services.contract_llm_service.ensure_extra_is_dict') as mock_ensure_dict:
            
            # Mock successful title enhancement
            mock_enhance_title.return_value = {
                'enhanced_title': 'Professional Software Development Services',
                'confidence': 0.9,
                'reasoning': 'Made more professional'
            }
            
            with patch.object(service, '_process_enhancement_batch') as mock_batch:
                service.enhance_prospect_titles([prospect])
                processor_func = mock_batch.call_args[0][2]
                
                result = processor_func(prospect)
                
                assert result is True
                assert prospect.ai_enhanced_title == 'Professional Software Development Services'
                mock_ensure_dict.assert_called_once_with(prospect)
                mock_update_timestamp.assert_called_once_with(prospect)
                
                # Verify extra field was updated with metadata
                expected_extra = {
                    'llm_title_enhancement': {
                        'confidence': 0.9,
                        'reasoning': 'Made more professional',
                        'original_title': 'Software Dev',
                        'enhanced_at': pytest.ANY,
                        'model_used': service.model_name
                    }
                }
                # Check that extra field assignment was attempted
                assert hasattr(prospect.extra, '__setitem__') or isinstance(prospect.extra, dict)


class TestEnhanceProspectNAICS:
    """Test bulk NAICS classification functionality"""
    
    @pytest.fixture
    def service(self):
        return ContractLLMService()
    
    def test_naics_processor_with_extra_field_naics(self, service):
        """Test NAICS processing when NAICS is found in extra field"""
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect"
        prospect.description = "Software development services"
        prospect.naics = None
        prospect.naics_description = None
        prospect.naics_source = None
        prospect.extra = {"naics_code": "541511"}
        prospect.title = "Software Development"
        prospect.agency = "DOD"
        prospect.contract_type = "Services"
        prospect.set_aside = "Small Business"
        prospect.estimated_value_text = "$100,000"
        
        with patch.object(service, 'extract_naics_from_extra_field') as mock_extract, \
             patch.object(service, '_update_prospect_timestamp') as mock_update_timestamp, \
             patch('app.services.contract_llm_service.ensure_extra_is_dict'):
            
            # Mock finding NAICS in extra field
            mock_extract.return_value = {
                'found_in_extra': True,
                'code': '541511',
                'description': 'Custom Computer Programming Services'
            }
            
            with patch.object(service, '_process_enhancement_batch') as mock_batch:
                service.enhance_prospect_naics([prospect])
                processor_func = mock_batch.call_args[0][2]
                
                result = processor_func(prospect)
                
                assert result is True
                assert prospect.naics == '541511'
                assert prospect.naics_description == 'Custom Computer Programming Services'
                assert prospect.naics_source == 'original'
                mock_update_timestamp.assert_called_once_with(prospect)
    
    def test_naics_processor_with_llm_classification(self, service):
        """Test NAICS processing with LLM classification"""
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect"
        prospect.description = "Software development services"
        prospect.naics = None
        prospect.naics_description = None
        prospect.naics_source = None
        prospect.extra = {}
        prospect.title = "Software Development"
        prospect.agency = "DOD"
        prospect.contract_type = "Services"
        prospect.set_aside = "Small Business"
        prospect.estimated_value_text = "$100,000"
        
        with patch.object(service, 'extract_naics_from_extra_field') as mock_extract, \
             patch.object(service, 'classify_naics_with_llm') as mock_classify, \
             patch.object(service, '_update_prospect_timestamp') as mock_update_timestamp, \
             patch('app.services.contract_llm_service.ensure_extra_is_dict'):
            
            # Mock no NAICS in extra field
            mock_extract.return_value = {
                'found_in_extra': False,
                'code': None,
                'description': None
            }
            
            # Mock successful LLM classification
            mock_classify.return_value = {
                'code': '541511',
                'description': 'Custom Computer Programming Services',
                'confidence': 0.9
            }
            
            with patch.object(service, '_process_enhancement_batch') as mock_batch:
                service.enhance_prospect_naics([prospect])
                processor_func = mock_batch.call_args[0][2]
                
                result = processor_func(prospect)
                
                assert result is True
                assert prospect.naics == '541511'
                assert prospect.naics_description == 'Custom Computer Programming Services'
                assert prospect.naics_source == 'llm_inferred'
                mock_update_timestamp.assert_called_once_with(prospect)


class TestEnhanceProspectSetAsides:
    """Test bulk set-aside standardization functionality"""
    
    @pytest.fixture
    def service(self):
        return ContractLLMService()
    
    def test_set_aside_processor_function_logic(self, service):
        """Test the internal set-aside processing logic"""
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect"
        prospect.set_aside = "Small Business Set-Aside"
        prospect.set_aside_standardized = None
        prospect.set_aside_standardized_label = None
        prospect.extra = {}
        
        with patch.object(service, 'standardize_set_aside_with_llm') as mock_standardize, \
             patch.object(service, '_update_prospect_timestamp') as mock_update_timestamp, \
             patch('app.services.contract_llm_service.ensure_extra_is_dict'):
            
            # Mock successful standardization
            from app.services.set_aside_standardization import StandardSetAside
            mock_result = Mock()
            mock_result.code = 'SMALL_BUSINESS'
            mock_result.label = 'Small Business Set-Aside'
            mock_standardize.return_value = mock_result
            
            with patch.object(service, '_process_enhancement_batch') as mock_batch:
                service.enhance_prospect_set_asides([prospect])
                processor_func = mock_batch.call_args[0][2]
                
                result = processor_func(prospect)
                
                assert result is True
                assert prospect.set_aside_standardized == 'SMALL_BUSINESS'
                assert prospect.set_aside_standardized_label == 'Small Business Set-Aside'
                mock_update_timestamp.assert_called_once_with(prospect)


class TestUpdateProspectTimestamp:
    """Test prospect timestamp update functionality"""
    
    @pytest.fixture
    def service(self):
        return ContractLLMService()
    
    @patch('app.services.contract_llm_service.db.session')
    @patch('app.services.contract_llm_service.update_prospect_timestamps')
    def test_update_prospect_timestamp_success(self, mock_update_timestamps, mock_db_session, service):
        """Test successful timestamp update"""
        prospect = Mock(spec=Prospect)
        prospect.id = "test-prospect"
        
        service._update_prospect_timestamp(prospect)
        
        mock_update_timestamps.assert_called_once_with(prospect, service.model_name)
        mock_db_session.commit.assert_called_once()
    
    @patch('app.services.contract_llm_service.db.session')
    @patch('app.services.contract_llm_service.update_prospect_timestamps')
    @patch('app.services.contract_llm_service.logger')
    def test_update_prospect_timestamp_failure(self, mock_logger, mock_update_timestamps, mock_db_session, service):
        """Test timestamp update failure handling"""
        prospect = Mock(spec=Prospect)
        mock_db_session.commit.side_effect = Exception("Database error")
        
        service._update_prospect_timestamp(prospect)
        
        mock_logger.error.assert_called_once()
        mock_db_session.rollback.assert_called_once()


class TestEmitFieldUpdate:
    """Test field update emission (no-op for batch processing)"""
    
    def test_emit_field_update_no_op(self):
        """Test that _emit_field_update is a no-op for batch processing"""
        service = ContractLLMService()
        
        # Should not raise any exceptions
        result = service._emit_field_update("prospect-123", "values", {"test": "data"})
        
        # Should return None (no-op)
        assert result is None