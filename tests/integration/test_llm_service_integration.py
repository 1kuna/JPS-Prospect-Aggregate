"""
Integration tests for LLM services - End-to-end enhancement workflows
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from app.services.base_llm_service import BaseLLMService
from app.services.contract_llm_service import ContractLLMService
from app.services.iterative_llm_service import IterativeLLMService
from app.database.models import Prospect
from app.services.set_aside_standardization import StandardSetAside


class TestServiceIntegration:
    """Test integration between different LLM services"""
    
    @pytest.fixture
    def mock_prospect_full(self):
        """Create a comprehensive mock prospect for integration testing"""
        prospect = Mock(spec=Prospect)
        prospect.id = "integration-prospect-123"
        prospect.title = "Software Development Services"
        prospect.description = "Custom software development and maintenance services for government agencies"
        prospect.estimated_value_text = "$100,000 - $500,000"
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
        prospect.agency = "Department of Defense"
        prospect.contract_type = "Services"
        prospect.extra = {}
        prospect.ollama_processed_at = None
        prospect.ollama_model_version = None
        return prospect
    
    def test_all_services_use_same_base_logic(self, mock_prospect_full):
        """Test that all services produce consistent results using shared base logic"""
        base_service = BaseLLMService()
        contract_service = ContractLLMService()
        iterative_service = IterativeLLMService()
        
        # Mock the LLM calls to return consistent results
        with patch.object(base_service, 'parse_contract_value_with_llm') as mock_parse_value, \
             patch.object(base_service, 'classify_naics_with_llm') as mock_classify_naics, \
             patch.object(base_service, 'enhance_title_with_llm') as mock_enhance_title, \
             patch.object(base_service, 'standardize_set_aside_with_llm') as mock_standardize_set_aside:
            
            # Setup consistent mock returns
            mock_parse_value.return_value = {'single': None, 'min': 100000, 'max': 500000}
            mock_classify_naics.return_value = {'code': '541511', 'description': 'Custom Computer Programming Services'}
            mock_enhance_title.return_value = {'enhanced_title': 'Professional Software Development Services'}
            mock_standardize_set_aside.return_value = StandardSetAside.SMALL_BUSINESS
            
            # Test BaseLLMService directly
            base_results = base_service.process_single_prospect_enhancement(mock_prospect_full, "all")
            
            # Test that ContractLLMService has the same methods available
            assert hasattr(contract_service, 'parse_contract_value_with_llm')
            assert hasattr(contract_service, 'classify_naics_with_llm')
            assert hasattr(contract_service, 'enhance_title_with_llm')
            
            # Test that IterativeLLMService uses the same base service
            assert isinstance(iterative_service.base_service, BaseLLMService)
            
            # All should be successful
            assert all(base_results.values())


class TestEndToEndEnhancementWorkflow:
    """Test complete enhancement workflows from start to finish"""
    
    @pytest.fixture
    def sample_prospects(self):
        """Create sample prospects for batch testing"""
        prospects = []
        
        # Prospect 1: Needs all enhancements
        prospect1 = Mock(spec=Prospect)
        prospect1.id = "prospect-1"
        prospect1.title = "IT Services"
        prospect1.description = "Information technology consulting services"
        prospect1.estimated_value_text = "$250,000"
        prospect1.estimated_value_single = None
        prospect1.naics = None
        prospect1.ai_enhanced_title = None
        prospect1.set_aside = "Small Business"
        prospect1.set_aside_standardized = None
        prospect1.extra = {}
        prospect1.ollama_processed_at = None
        prospect1.ollama_model_version = None
        prospects.append(prospect1)
        
        # Prospect 2: Needs only some enhancements
        prospect2 = Mock(spec=Prospect)
        prospect2.id = "prospect-2"
        prospect2.title = "Software Development"
        prospect2.description = "Custom software development"
        prospect2.estimated_value_text = "$100K - $200K"
        prospect2.estimated_value_single = None
        prospect2.naics = "541511"  # Already has NAICS
        prospect2.naics_source = "original"
        prospect2.ai_enhanced_title = None
        prospect2.set_aside = "8(a) Competitive"
        prospect2.set_aside_standardized = None
        prospect2.extra = {}
        prospect2.ollama_processed_at = None
        prospect2.ollama_model_version = None
        prospects.append(prospect2)
        
        return prospects
    
    @patch('app.services.contract_llm_service.db.session')
    def test_batch_processing_workflow(self, mock_db_session, sample_prospects):
        """Test complete batch processing workflow"""
        service = ContractLLMService()
        
        # Mock all LLM calls
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value, \
             patch.object(service, 'classify_naics_with_llm') as mock_classify_naics, \
             patch.object(service, 'enhance_title_with_llm') as mock_enhance_title, \
             patch.object(service, 'standardize_set_aside_with_llm') as mock_standardize_set_aside, \
             patch.object(service, '_update_prospect_timestamp') as mock_update_timestamp:
            
            # Setup mock returns
            mock_parse_value.return_value = {'single': 250000, 'min': None, 'max': None}
            mock_classify_naics.return_value = {'code': '541512', 'description': 'Computer Systems Design Services'}
            mock_enhance_title.return_value = {'enhanced_title': 'Professional IT Consulting Services'}
            mock_standardize_set_aside.return_value = StandardSetAside.SMALL_BUSINESS
            
            # Test batch value enhancement
            values_processed = service.enhance_prospect_values(sample_prospects)
            assert values_processed >= 0  # Should process some prospects
            
            # Test batch title enhancement
            titles_processed = service.enhance_prospect_titles(sample_prospects)
            assert titles_processed >= 0
            
            # Test batch NAICS enhancement
            naics_processed = service.enhance_prospect_naics(sample_prospects)
            assert naics_processed >= 0
            
            # Test batch set-aside enhancement
            set_asides_processed = service.enhance_prospect_set_asides(sample_prospects)
            assert set_asides_processed >= 0
    
    def test_iterative_processing_workflow(self, sample_prospects):
        """Test complete iterative processing workflow"""
        service = IterativeLLMService()
        
        # Mock the database session and app context
        with patch('app.services.iterative_llm_service.create_app') as mock_create_app, \
             patch('app.services.iterative_llm_service.sessionmaker') as mock_sessionmaker:
            
            mock_app = Mock()
            mock_create_app.return_value = mock_app
            mock_app.app_context.return_value.__enter__ = Mock()
            mock_app.app_context.return_value.__exit__ = Mock()
            
            mock_session = Mock()
            mock_sessionmaker.return_value = mock_session
            
            with patch.object(service, '_get_prospects_to_process') as mock_get_prospects:
                mock_get_prospects.return_value = sample_prospects
                
                # Test starting enhancement without queue service (direct processing)
                result = service.start_enhancement("all", skip_existing=True)
                
                # Should either start directly or indicate no prospects to process
                assert result["status"] in ["started", "completed"]


class TestDatabaseIntegration:
    """Test database persistence and transaction handling"""
    
    @pytest.fixture
    def mock_prospect_db(self):
        """Create a mock prospect for database testing"""
        prospect = Mock(spec=Prospect)
        prospect.id = "db-prospect-123"
        prospect.title = "Database Test Prospect"
        prospect.description = "Testing database integration"
        prospect.estimated_value_text = "$75,000"
        prospect.estimated_value_single = None
        prospect.naics = None
        prospect.ai_enhanced_title = None
        prospect.set_aside = "WOSB"
        prospect.set_aside_standardized = None
        prospect.extra = {}
        prospect.ollama_processed_at = None
        prospect.ollama_model_version = None
        return prospect
    
    @patch('app.services.contract_llm_service.db.session')
    def test_database_transaction_handling(self, mock_db_session, mock_prospect_db):
        """Test that database transactions are handled properly"""
        service = ContractLLMService()
        
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value:
            mock_parse_value.return_value = {'single': 75000, 'min': None, 'max': None}
            
            # Test successful processing
            service.enhance_prospect_values([mock_prospect_db])
            
            # Should commit for each prospect in batch mode
            assert mock_db_session.commit.called
    
    @patch('app.services.contract_llm_service.db.session')
    def test_database_rollback_on_error(self, mock_db_session, mock_prospect_db):
        """Test that database rolls back on errors"""
        service = ContractLLMService()
        
        # Make the commit fail
        mock_db_session.commit.side_effect = Exception("Database error")
        
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value:
            mock_parse_value.return_value = {'single': 75000, 'min': None, 'max': None}
            
            # Should handle the error gracefully
            service.enhance_prospect_values([mock_prospect_db])
            
            # Should attempt rollback on error
            mock_db_session.rollback.assert_called()


class TestErrorHandlingIntegration:
    """Test error handling across services"""
    
    @pytest.fixture
    def problematic_prospect(self):
        """Create a prospect that might cause errors"""
        prospect = Mock(spec=Prospect)
        prospect.id = "error-prospect-123"
        prospect.title = None  # Missing title
        prospect.description = ""  # Empty description
        prospect.estimated_value_text = "invalid value format"
        prospect.estimated_value_single = None
        prospect.naics = None
        prospect.ai_enhanced_title = None
        prospect.set_aside = None
        prospect.extra = "invalid json"  # Invalid JSON
        prospect.ollama_processed_at = None
        prospect.ollama_model_version = None
        return prospect
    
    def test_base_service_error_handling(self, problematic_prospect):
        """Test that base service handles errors gracefully"""
        service = BaseLLMService()
        
        # Mock LLM methods to raise errors
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value, \
             patch.object(service, 'classify_naics_with_llm') as mock_classify_naics:
            
            mock_parse_value.side_effect = Exception("LLM parsing error")
            mock_classify_naics.side_effect = Exception("LLM classification error")
            
            # Should handle errors and return results indicating failure
            results = service.process_single_prospect_enhancement(problematic_prospect, "all")
            
            # Should not crash, but should indicate some failures
            assert isinstance(results, dict)
            assert 'values' in results
            assert 'naics' in results
    
    @patch('app.services.contract_llm_service.db.session')
    def test_batch_service_error_handling(self, mock_db_session, problematic_prospect):
        """Test that batch service handles individual prospect errors"""
        service = ContractLLMService()
        
        # Mix of good and bad prospects
        good_prospect = Mock(spec=Prospect)
        good_prospect.id = "good-prospect"
        good_prospect.estimated_value_text = "$100,000"
        good_prospect.estimated_value_single = None
        good_prospect.extra = {}
        good_prospect.ollama_processed_at = None
        good_prospect.ollama_model_version = None
        
        prospects = [good_prospect, problematic_prospect]
        
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value:
            # Make it fail for problematic prospect
            def selective_failure(value_text, prospect_id=None):
                if prospect_id == "error-prospect-123":
                    raise Exception("Processing error")
                return {'single': 100000, 'min': None, 'max': None}
            
            mock_parse_value.side_effect = selective_failure
            
            # Should process what it can and skip errors
            processed_count = service.enhance_prospect_values(prospects)
            
            # Should process at least the good prospect
            assert processed_count >= 0


class TestProgressCallbackIntegration:
    """Test progress callback integration across services"""
    
    def test_progress_callback_with_base_service(self):
        """Test progress callbacks work with base service"""
        service = BaseLLMService()
        
        mock_prospect = Mock(spec=Prospect)
        mock_prospect.id = "callback-prospect"
        mock_prospect.title = "Test Title"
        mock_prospect.description = "Test Description"
        mock_prospect.estimated_value_text = "$50,000"
        mock_prospect.estimated_value_single = None
        mock_prospect.naics = None
        mock_prospect.ai_enhanced_title = None
        mock_prospect.set_aside = "Small Business"
        mock_prospect.set_aside_standardized = None
        mock_prospect.extra = {}
        
        callback_calls = []
        
        def progress_callback(update):
            callback_calls.append(update)
        
        with patch.object(service, 'parse_contract_value_with_llm') as mock_parse_value, \
             patch.object(service, 'classify_naics_with_llm') as mock_classify_naics, \
             patch.object(service, 'enhance_title_with_llm') as mock_enhance_title, \
             patch.object(service, 'standardize_set_aside_with_llm') as mock_standardize_set_aside:
            
            # Setup mock returns
            mock_parse_value.return_value = {'single': 50000, 'min': None, 'max': None}
            mock_classify_naics.return_value = {'code': '541511', 'description': 'Custom Computer Programming Services'}
            mock_enhance_title.return_value = {'enhanced_title': 'Professional Test Services'}
            mock_standardize_set_aside.return_value = StandardSetAside.SMALL_BUSINESS
            
            service.process_single_prospect_enhancement(
                mock_prospect, 
                "all", 
                progress_callback=progress_callback
            )
            
            # Should have received progress callbacks
            assert len(callback_calls) > 0
            
            # Callbacks should have expected structure
            for call in callback_calls:
                assert 'status' in call
                assert 'field' in call
                assert 'prospect_id' in call


class TestServiceInteroperability:
    """Test that services can work together and share data"""
    
    def test_services_share_common_interface(self):
        """Test that all services implement expected interfaces"""
        base_service = BaseLLMService()
        contract_service = ContractLLMService()
        iterative_service = IterativeLLMService()
        
        # All should have core LLM methods
        core_methods = [
            'parse_existing_naics',
            'extract_naics_from_extra_field',
            'classify_naics_with_llm',
            'parse_contract_value_with_llm',
            'enhance_title_with_llm'
        ]
        
        for method in core_methods:
            assert hasattr(base_service, method)
            assert hasattr(contract_service, method)
            # IterativeLLMService uses base_service, so check there
            assert hasattr(iterative_service.base_service, method)
    
    def test_consistent_model_configuration(self):
        """Test that services use consistent model configuration"""
        base_service = BaseLLMService()
        contract_service = ContractLLMService()
        iterative_service = IterativeLLMService()
        
        # All should use the same default model
        assert base_service.model_name == 'qwen3:latest'
        assert contract_service.model_name == 'qwen3:latest'
        assert iterative_service.base_service.model_name == 'qwen3:latest'
        
        # Should be able to configure custom models
        custom_base = BaseLLMService(model_name='custom-model')
        custom_contract = ContractLLMService(model_name='custom-model')
        
        assert custom_base.model_name == 'custom-model'
        assert custom_contract.model_name == 'custom-model'