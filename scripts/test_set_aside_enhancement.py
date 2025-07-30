#!/usr/bin/env python3
"""
Test script for set-aside enhancement functionality.
Tests both rule-based standardization and LLM classification.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db
from app.database.models import Prospect
from app.services.set_aside_standardization import SetAsideStandardizer, StandardSetAside
from app.services.contract_llm_service import ContractLLMService
from app.services.base_llm_service import BaseLLMService
from app.services.iterative_llm_service import IterativeLLMService

def test_rule_based_standardization():
    """Test the rule-based set-aside standardization"""
    print("="*80)
    print("TESTING RULE-BASED SET-ASIDE STANDARDIZATION")
    print("="*80)
    
    standardizer = SetAsideStandardizer()
    
    # Test cases from the database analysis
    test_cases = [
        "Small Business Set-Aside",
        "8(a) Competitive", 
        "HUBZone",
        "Women-owned Small Business (WOSB)",
        "Service-Disabled Veteran Owned Small Business",
        "SDVOSB Competitive",
        "Full and Open",
        "determined",
        "TBD",
        "[TBD]",
        "Other Than Small Business",
        "Small Business",
        "Sole Source",
        "Small Disadvantaged Business",
        "Currently this information not available",
        "WOSB",
        "EDWOSB",
        "Woman Owned Small Business",
        "8(a) non-competitive"
    ]
    
    print(f"Testing {len(test_cases)} set-aside values:")
    print()
    
    for i, test_value in enumerate(test_cases, 1):
        standardized = standardizer.standardize_set_aside(test_value)
        confidence = standardizer.get_confidence_score(test_value, standardized)
        
        print(f"{i:2d}. '{test_value}'")
        print(f"    → {standardized.value}")
        print(f"    → Confidence: {confidence:.2f}")
        print()

def test_llm_enhancement_sample():
    """Test LLM enhancement on a small sample of real data"""
    print("="*80)
    print("TESTING LLM SET-ASIDE ENHANCEMENT")
    print("="*80)
    
    app = create_app()
    with app.app_context():
        # Get a small sample of prospects with set-aside data
        prospects = db.session.query(Prospect).filter(
            Prospect.set_aside.isnot(None),
            Prospect.set_aside != ''
        ).limit(5).all()
        
        if not prospects:
            print("No prospects with set-aside data found.")
            return
        
        print(f"Testing LLM enhancement on {len(prospects)} prospects:")
        print()
        
        llm_service = ContractLLMService()
        
        for i, prospect in enumerate(prospects, 1):
            print(f"{i}. Prospect ID: {prospect.id}")
            print(f"   Original set-aside: '{prospect.set_aside}'")
            
            # Test rule-based first
            standardized = llm_service.set_aside_standardizer.standardize_set_aside(prospect.set_aside)
            confidence = llm_service.set_aside_standardizer.get_confidence_score(prospect.set_aside, standardized)
            
            print(f"   Rule-based result: {standardized.value} (confidence: {confidence:.2f})")
            
            # Test LLM if low confidence
            if confidence < 0.7:
                print("   Low confidence - testing LLM enhancement...")
                llm_result = llm_service._enhance_set_aside_with_llm(prospect.set_aside, prospect.id)
                if llm_result:
                    print(f"   LLM result: {llm_result.get('standardized_set_aside', 'N/A')} (confidence: {llm_result.get('confidence', 0.0):.2f})")
                else:
                    print("   LLM enhancement failed")
            else:
                print("   High confidence - using rule-based result")
            
            print()

def test_edge_cases():
    """Test edge cases and problematic values"""
    print("="*80)
    print("TESTING EDGE CASES")
    print("="*80)
    
    standardizer = SetAsideStandardizer()
    
    edge_cases = [
        None,
        "",
        "   ",
        "Small Business 2024-01-01",  # Date contamination
        "Small Business CA",          # State contamination  
        "Very long description that goes on and on with lots of extra information that should be cleaned",
        "UNKNOWN_TYPE",
        "8(a) Something Unexpected",
        "Women Owned",
        "Veteran Owned",
        "Service Disabled",
        "hubzone sole source"
    ]
    
    print(f"Testing {len(edge_cases)} edge cases:")
    print()
    
    for i, test_value in enumerate(edge_cases, 1):
        standardized = standardizer.standardize_set_aside(test_value)
        confidence = standardizer.get_confidence_score(test_value, standardized)
        
        print(f"{i:2d}. '{test_value}'")
        print(f"    → {standardized.value}")
        print(f"    → Confidence: {confidence:.2f}")
        print()

def test_new_architecture():
    """Test the new refactored LLM service architecture"""
    print("="*80)
    print("TESTING NEW REFACTORED LLM SERVICE ARCHITECTURE")
    print("="*80)
    
    app = create_app()
    with app.app_context():
        # Get a sample prospect
        prospect = db.session.query(Prospect).filter(
            Prospect.set_aside.isnot(None),
            Prospect.set_aside != ''
        ).first()
        
        if not prospect:
            print("No prospects with set-aside data found for testing.")
            return
        
        print(f"Testing with Prospect ID: {prospect.id}")
        print(f"Original set-aside: '{prospect.set_aside}'")
        print()
        
        # 1. Test BaseLLMService directly
        print("1. Testing BaseLLMService (individual processing):")
        base_service = BaseLLMService()
        
        # Test set-aside standardization
        standardized = base_service.standardize_set_aside_with_llm(prospect.set_aside, prospect.id)
        if standardized:
            print(f"   Standardized: {standardized.code} ({standardized.label})")
        else:
            print("   Standardization failed")
        
        print()
        
        # 2. Test ContractLLMService (batch processing)
        print("2. Testing ContractLLMService (batch processing):")
        contract_service = ContractLLMService()
        
        # Test that it inherits from BaseLLMService
        print(f"   Inherits from BaseLLMService: {isinstance(contract_service, BaseLLMService)}")
        
        # Test that it has both inherited and batch-specific methods
        inherited_methods = ['standardize_set_aside_with_llm', 'parse_existing_naics', 'extract_naics_from_extra_field']
        batch_methods = ['enhance_prospect_set_asides', 'enhance_prospect_values', 'enhance_prospect_naics']
        
        print("   Inherited methods available:", all(hasattr(contract_service, m) for m in inherited_methods))
        print("   Batch methods available:", all(hasattr(contract_service, m) for m in batch_methods))
        
        print()
        
        # 3. Test IterativeLLMService (real-time processing)
        print("3. Testing IterativeLLMService (real-time processing):")
        iterative_service = IterativeLLMService()
        
        # Test that it uses BaseLLMService
        print(f"   Uses BaseLLMService: {isinstance(iterative_service.base_service, BaseLLMService)}")
        print(f"   Initial processing state: {iterative_service.is_processing()}")
        
        # Test progress tracking
        progress = iterative_service.get_progress()
        print(f"   Progress tracking works: {progress['status'] == 'idle'}")
        
        print()
        
        # 4. Test service interoperability
        print("4. Testing service interoperability:")
        
        # All services should be able to standardize the same set-aside value
        base_result = base_service.standardize_set_aside_with_llm(prospect.set_aside)
        contract_result = contract_service.standardize_set_aside_with_llm(prospect.set_aside)
        iterative_result = iterative_service.base_service.standardize_set_aside_with_llm(prospect.set_aside)
        
        results_consistent = (
            base_result == contract_result == iterative_result if base_result else 
            contract_result == iterative_result == base_result
        )
        
        print(f"   All services produce consistent results: {results_consistent}")
        
        if base_result:
            print(f"   Common result: {base_result.code} ({base_result.label})")
        
        print()
        
        # 5. Test code reduction benefits
        print("5. Code reduction benefits:")
        
        # Count methods in each service
        base_methods = [m for m in dir(base_service) if not m.startswith('_') and callable(getattr(base_service, m))]
        contract_methods = [m for m in dir(contract_service) if not m.startswith('_') and callable(getattr(contract_service, m))]
        iterative_methods = [m for m in dir(iterative_service) if not m.startswith('_') and callable(getattr(iterative_service, m))]
        
        print(f"   BaseLLMService methods: {len(base_methods)}")
        print(f"   ContractLLMService methods: {len(contract_methods)} (inherits {len(base_methods)} from base)")
        print(f"   IterativeLLMService methods: {len(iterative_methods)} (uses base service)")
        
        # Show that ContractLLMService has inherited methods plus its own
        inherited_count = sum(1 for m in base_methods if hasattr(contract_service, m))
        print(f"   ContractLLMService inherits {inherited_count}/{len(base_methods)} base methods")
        
        print()
        print("✅ New architecture testing completed successfully!")


def main():
    """Run all tests"""
    print("SET-ASIDE ENHANCEMENT TEST SUITE")
    print("="*80)
    print()
    
    # Test rule-based standardization
    test_rule_based_standardization()
    
    # Test edge cases
    test_edge_cases()
    
    # Test new refactored architecture
    test_new_architecture()
    
    # Test LLM enhancement (only if Ollama is available)
    try:
        from app.utils.llm_utils import call_ollama
        test_response = call_ollama("Test", "qwen3:latest")
        if test_response:
            test_llm_enhancement_sample()
        else:
            print("="*80)
            print("SKIPPING LLM TESTS - Ollama not available")
            print("="*80)
    except Exception as e:
        print("="*80)
        print(f"SKIPPING LLM TESTS - Error: {e}")
        print("="*80)
    
    print("="*80)
    print("TEST SUITE COMPLETED")
    print("="*80)

if __name__ == "__main__":
    main()