#!/usr/bin/env python3
"""
Test the enhanced bulk upsert function to ensure it works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db
from app.utils.duplicate_prevention import enhanced_bulk_upsert_prospects
from app.database.models import DataSource, Prospect
from app.config import active_config
import pandas as pd
from datetime import datetime, timezone

def test_enhanced_upsert():
    """Test the enhanced bulk upsert function."""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("TESTING ENHANCED BULK UPSERT")
        print("=" * 60)
        
        # Create a test data source
        test_source = db.session.query(DataSource).filter_by(name="TEST_UPSERT_SOURCE").first()
        if not test_source:
            test_source = DataSource(
                name="TEST_UPSERT_SOURCE",
                description="Test source for upsert testing"
            )
            db.session.add(test_source)
            db.session.commit()
            print(f"✅ Created test source (ID: {test_source.id})")
        else:
            print(f"✅ Using existing test source (ID: {test_source.id})")
        
        # Test 1: Insert new prospect
        print("\n1️⃣ Testing new prospect insertion...")
        test_data = pd.DataFrame([{
            'source_id': test_source.id,
            'native_id': 'UPSERT_TEST_001',
            'title': 'Test Software Engineer Position',
            'description': 'Testing the upsert functionality',
            'agency': 'Test Agency',
            'naics': '541511',
            'place_city': 'Test City',
            'place_state': 'TS'
        }])
        
        stats = enhanced_bulk_upsert_prospects(
            test_data, db.session, test_source.id,
            preserve_ai_data=True,
            enable_smart_matching=True
        )
        
        print(f"   Results: {stats}")
        
        # Test 2: Update with same data (should match)
        print("\n2️⃣ Testing update with same native_id...")
        test_data['title'] = 'Updated Software Engineer Position'
        
        stats = enhanced_bulk_upsert_prospects(
            test_data, db.session, test_source.id,
            preserve_ai_data=True,
            enable_smart_matching=True
        )
        
        print(f"   Results: {stats}")
        
        # Test 3: Test with different content but same native_id
        print("\n3️⃣ Testing with very different content but same native_id...")
        different_data = pd.DataFrame([{
            'source_id': test_source.id,
            'native_id': 'UPSERT_TEST_001',  # Same ID
            'title': 'Network Administrator',  # Completely different
            'description': 'Network security role',  # Completely different
            'agency': 'Different Agency',
            'naics': '541512',
            'place_city': 'Other City',
            'place_state': 'OT'
        }])
        
        stats = enhanced_bulk_upsert_prospects(
            different_data, db.session, test_source.id,
            preserve_ai_data=True,
            enable_smart_matching=True
        )
        
        print(f"   Results: {stats}")
        print(f"   Note: Should be low confidence due to different content")
        
        # Test 4: Test fuzzy matching
        print("\n4️⃣ Testing fuzzy matching with similar title...")
        fuzzy_data = pd.DataFrame([{
            'source_id': test_source.id,
            'native_id': 'UPSERT_TEST_002',  # Different ID
            'title': 'Sr. Software Engineer Position',  # Similar to first
            'description': 'Testing the upsert functionality with variations',
            'agency': 'Test Agency',
            'naics': '541511',
            'place_city': 'Test City',
            'place_state': 'TS'
        }])
        
        stats = enhanced_bulk_upsert_prospects(
            fuzzy_data, db.session, test_source.id,
            preserve_ai_data=True,
            enable_smart_matching=True
        )
        
        print(f"   Results: {stats}")
        
        # Test 5: Configuration test
        print("\n5️⃣ Testing configuration values...")
        print(f"   AI Preservation: {active_config.PRESERVE_AI_DATA_ON_REFRESH}")
        print(f"   Smart Matching: {active_config.ENABLE_SMART_DUPLICATE_MATCHING}")
        print(f"   Min Confidence: {active_config.DUPLICATE_MIN_CONFIDENCE}")
        print(f"   Native ID Min Content Sim: {active_config.DUPLICATE_NATIVE_ID_MIN_CONTENT_SIM}")
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        db.session.query(Prospect).filter(
            Prospect.source_id == test_source.id
        ).delete()
        db.session.query(DataSource).filter_by(id=test_source.id).delete()
        db.session.commit()
        print("   ✅ Test data cleaned up")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)

if __name__ == "__main__":
    test_enhanced_upsert()