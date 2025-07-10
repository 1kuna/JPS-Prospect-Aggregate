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

def main():
    """Run all tests"""
    print("SET-ASIDE ENHANCEMENT TEST SUITE")
    print("="*80)
    print()
    
    # Test rule-based standardization
    test_rule_based_standardization()
    
    # Test edge cases
    test_edge_cases()
    
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