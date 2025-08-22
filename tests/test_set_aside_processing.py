#!/usr/bin/env python
"""
Test script to verify set-aside LLM processing works end-to-end.
Uses real test data from fixtures to ensure realistic testing.
"""

import sys
import os
import pandas as pd
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database.models import Prospect, db
from app.services.llm_service import LLMService
from app.utils.logger import logger


def load_test_data_with_set_asides():
    """Load test data from fixtures that have set-aside information."""
    test_files = [
        "tests/fixtures/golden_files/doj_scraper/doj_sample_data.csv",
        "tests/fixtures/golden_files/doc_scraper/doc_sample_data.csv",
        "tests/fixtures/golden_files/acquisition_gateway/acquisition_gateway_sample.csv",
    ]
    
    prospects_with_set_asides = []
    
    for file_path in test_files:
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                # Check for set-aside columns
                set_aside_columns = [col for col in df.columns if 'set' in col.lower() and 'aside' in col.lower()]
                if set_aside_columns:
                    # Get rows with set-aside data
                    for col in set_aside_columns:
                        rows_with_data = df[df[col].notna() & (df[col] != '')]
                        if not rows_with_data.empty:
                            for _, row in rows_with_data.iterrows():
                                prospects_with_set_asides.append({
                                    'source_file': file_path,
                                    'set_aside_column': col,
                                    'set_aside_value': row[col],
                                    'title': row.get('Title', row.get('title', 'Test Prospect')),
                                    'agency': row.get('Agency', row.get('agency', 'Test Agency')),
                                    'row_data': row.to_dict()
                                })
                logger.info(f"Found {len(prospects_with_set_asides)} prospects with set-aside data in {file_path}")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
    
    return prospects_with_set_asides


def create_test_prospects(app, test_data):
    """Create test prospects in the database."""
    created_prospects = []
    
    with app.app_context():
        for data in test_data[:5]:  # Limit to 5 for testing
            # Create a unique ID for testing
            import uuid
            prospect_id = str(uuid.uuid4())
            
            prospect = Prospect(
                id=prospect_id,
                title=data['title'],
                agency=data['agency'],
                set_aside=data['set_aside_value'],
                extra={'test_data': True, 'source_file': data['source_file'], 'source': data['source_file'].split('/')[-2]}
            )
            
            db.session.add(prospect)
            created_prospects.append(prospect_id)
            logger.info(f"Created test prospect {prospect_id[:8]}... with set-aside: {data['set_aside_value']}")
        
        db.session.commit()
        logger.info(f"Created {len(created_prospects)} test prospects in database")
    
    return created_prospects


def test_set_aside_enhancement(app, prospect_ids):
    """Test the set-aside enhancement process."""
    with app.app_context():
        llm_service = LLMService(model_name="qwen3:latest")
        
        results = {
            'total': len(prospect_ids),
            'processed': 0,
            'standardized': 0,
            'failed': 0,
            'details': []
        }
        
        for prospect_id in prospect_ids:
            prospect = Prospect.query.get(prospect_id)
            if not prospect:
                logger.error(f"Prospect {prospect_id} not found")
                results['failed'] += 1
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing prospect {prospect_id[:8]}...")
            logger.info(f"Original set-aside: {prospect.set_aside}")
            logger.info(f"Current standardized: {prospect.set_aside_standardized}")
            
            # Test the enhancement
            try:
                enhancement_result = llm_service.enhance_single_prospect(
                    prospect, 
                    enhancement_type="set_asides",
                    force_redo=True
                )
                
                # Refresh the prospect to get updated values
                db.session.refresh(prospect)
                
                result_detail = {
                    'id': prospect_id[:8],
                    'original': prospect.set_aside,
                    'standardized': prospect.set_aside_standardized,
                    'standardized_label': prospect.set_aside_standardized_label,
                    'success': enhancement_result.get('set_asides', False)
                }
                
                results['details'].append(result_detail)
                results['processed'] += 1
                
                if prospect.set_aside_standardized:
                    results['standardized'] += 1
                    logger.info(f"✅ Successfully standardized to: {prospect.set_aside_standardized} ({prospect.set_aside_standardized_label})")
                else:
                    logger.warning(f"⚠️ No standardization occurred")
                    
            except Exception as e:
                logger.error(f"❌ Error processing prospect {prospect_id[:8]}: {e}")
                results['failed'] += 1
                results['details'].append({
                    'id': prospect_id[:8],
                    'error': str(e)
                })
        
        # Commit any changes
        db.session.commit()
        
        return results


def print_results(results):
    """Print test results in a formatted way."""
    print("\n" + "="*60)
    print("SET-ASIDE PROCESSING TEST RESULTS")
    print("="*60)
    print(f"Total prospects tested: {results['total']}")
    print(f"Successfully processed: {results['processed']}")
    print(f"Successfully standardized: {results['standardized']}")
    print(f"Failed: {results['failed']}")
    print(f"Success rate: {(results['standardized']/results['total']*100):.1f}%")
    
    print("\n" + "-"*60)
    print("DETAILED RESULTS:")
    print("-"*60)
    
    for detail in results['details']:
        if 'error' in detail:
            print(f"❌ {detail['id']}: ERROR - {detail['error']}")
        else:
            if detail['success']:
                print(f"✅ {detail['id']}: '{detail['original']}' → '{detail['standardized']}' ({detail['standardized_label']})")
            else:
                print(f"⚠️ {detail['id']}: '{detail['original']}' → No standardization")
    
    print("="*60 + "\n")


def cleanup_test_data(app, prospect_ids):
    """Clean up test data after testing."""
    with app.app_context():
        for prospect_id in prospect_ids:
            prospect = Prospect.query.get(prospect_id)
            if prospect:
                db.session.delete(prospect)
        db.session.commit()
        logger.info(f"Cleaned up {len(prospect_ids)} test prospects")


def main():
    """Main test execution."""
    print("\n" + "="*60)
    print("TESTING SET-ASIDE LLM PROCESSING")
    print("="*60)
    
    # Create app
    app = create_app()
    
    # Load test data
    print("\n1. Loading test data from fixtures...")
    test_data = load_test_data_with_set_asides()
    
    if not test_data:
        print("❌ No test data found with set-aside information")
        return 1
    
    print(f"✅ Found {len(test_data)} prospects with set-aside data")
    
    # Create test prospects
    print("\n2. Creating test prospects in database...")
    prospect_ids = create_test_prospects(app, test_data)
    
    if not prospect_ids:
        print("❌ Failed to create test prospects")
        return 1
    
    print(f"✅ Created {len(prospect_ids)} test prospects")
    
    # Test enhancement
    print("\n3. Testing set-aside enhancement...")
    results = test_set_aside_enhancement(app, prospect_ids)
    
    # Print results
    print_results(results)
    
    # Clean up
    print("4. Cleaning up test data...")
    cleanup_test_data(app, prospect_ids)
    print("✅ Test data cleaned up")
    
    # Return status code based on results
    if results['standardized'] > 0:
        print("\n✅ SET-ASIDE PROCESSING TEST PASSED")
        return 0
    else:
        print("\n❌ SET-ASIDE PROCESSING TEST FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())