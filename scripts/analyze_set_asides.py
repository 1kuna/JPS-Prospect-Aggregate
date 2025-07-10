#!/usr/bin/env python3
"""
Analyze set-aside field values in the database to understand current data patterns.
This helps inform the standardization mapping and LLM classification logic.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db
from app.database.models import Prospect, InferredProspectData
from app import create_app
from collections import Counter
import pandas as pd
import re

def clean_set_aside_value(value):
    """Clean a set-aside value for analysis"""
    if not value or pd.isna(value):
        return None
    
    # Convert to string and strip
    value = str(value).strip()
    
    # Remove common contamination patterns
    # Remove dates (YYYY-MM-DD, MM/DD/YYYY, etc.)
    value = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', value)
    value = re.sub(r'\b\d{1,2}/\d{1,2}/\d{4}\b', '', value)
    
    # Remove states and common location indicators
    state_patterns = [
        r'\b[A-Z]{2}\b',  # Two-letter state codes
        r'\bUnited States\b',
        r'\bUSA\b',
        r'\bU\.S\.\b',
    ]
    for pattern in state_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    
    # Remove extra whitespace and common separators
    value = re.sub(r'[,;|]+', ' ', value)
    value = re.sub(r'\s+', ' ', value)
    value = value.strip()
    
    return value if value else None

def analyze_set_aside_values():
    """Analyze all set-aside values in the database"""
    
    app = create_app()
    with app.app_context():
        # Get all prospects with set_aside data
        prospects = db.session.query(Prospect.set_aside).all()
        print(f"Total prospects: {len(prospects)}")
        
        # Get set_aside values
        set_aside_values = [p.set_aside for p in prospects if p.set_aside]
        print(f"Prospects with set_aside: {len(set_aside_values)}")
        
        # Get inferred set_aside values from the InferredProspectData table
        inferred_data = db.session.query(InferredProspectData.inferred_set_aside).all()
        inferred_values = [p.inferred_set_aside for p in inferred_data if p.inferred_set_aside]
        print(f"Prospects with inferred_set_aside: {len(inferred_values)}")
        
        # Clean and count set_aside values
        cleaned_set_asides = []
        for value in set_aside_values:
            cleaned = clean_set_aside_value(value)
            if cleaned:
                cleaned_set_asides.append(cleaned)
        
        set_aside_counter = Counter(cleaned_set_asides)
        
        # Clean and count inferred_set_aside values
        cleaned_inferred = []
        for value in inferred_values:
            cleaned = clean_set_aside_value(value)
            if cleaned:
                cleaned_inferred.append(cleaned)
        
        inferred_counter = Counter(cleaned_inferred)
        
        print("\n" + "="*80)
        print("SET_ASIDE FIELD ANALYSIS")
        print("="*80)
        
        print(f"\nTop 50 set_aside values (cleaned):")
        for value, count in set_aside_counter.most_common(50):
            print(f"{count:>6}: {value}")
        
        print("\n" + "="*80)
        print("INFERRED_SET_ASIDE FIELD ANALYSIS")  
        print("="*80)
        
        print(f"\nTop 50 inferred_set_aside values (cleaned):")
        for value, count in inferred_counter.most_common(50):
            print(f"{count:>6}: {value}")
        
        # Identify potential standard set-aside types
        print("\n" + "="*80)
        print("POTENTIAL STANDARD SET-ASIDE TYPES")
        print("="*80)
        
        # Common federal set-aside keywords
        keywords = [
            'small business', 'small bus', 'sb',
            '8(a)', 'eight a', 'eightA',
            'hubzone', 'hub zone', 'hzob',
            'wosb', 'women owned', 'woman owned', 'wo',
            'sdvosb', 'service disabled', 'veteran', 'vosb',
            'sdb', 'socially disadvantaged', 'disadvantaged',
            'large business', 'unrestricted', 'open',
            'total small business', 'tsb'
        ]
        
        print("\nFound values containing standard keywords:")
        all_values = set(cleaned_set_asides + cleaned_inferred)
        
        for keyword in keywords:
            matching = [v for v in all_values if keyword.lower() in v.lower()]
            if matching:
                print(f"\n'{keyword}' matches:")
                for match in sorted(matching)[:10]:  # Show up to 10 matches
                    print(f"  - {match}")
        
        # Show problematic values (likely contaminated)
        print("\n" + "="*80)
        print("POTENTIALLY CONTAMINATED VALUES")
        print("="*80)
        
        long_values = [v for v in all_values if len(v) > 50]
        print(f"\nValues longer than 50 characters ({len(long_values)} total):")
        for value in sorted(long_values)[:20]:  # Show first 20
            print(f"  - {value[:100]}{'...' if len(value) > 100 else ''}")
        
        # Values with numbers (likely dates or addresses)
        number_values = [v for v in all_values if re.search(r'\d{3,}', v)]
        print(f"\nValues with 3+ digit numbers ({len(number_values)} total):")
        for value in sorted(number_values)[:20]:  # Show first 20
            print(f"  - {value}")

if __name__ == "__main__":
    analyze_set_aside_values()