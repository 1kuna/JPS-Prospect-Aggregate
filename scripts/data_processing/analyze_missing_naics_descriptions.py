#!/usr/bin/env python3
"""Analyze NAICS codes in the database to identify missing descriptions.

This script identifies all NAICS codes in the prospects database that don't have
corresponding descriptions in the official NAICS lookup table.

Usage:
    python scripts/data_processing/analyze_missing_naics_descriptions.py [--export-csv]
"""

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.database import db
from app.database.models import Prospect
from app.utils.naics_lookup import NAICS_DESCRIPTIONS, get_naics_description
from sqlalchemy import func


def clean_naics_code(code):
    """Clean and standardize NAICS code."""
    if not code:
        return None
    
    # Handle TBD placeholder values
    if str(code).strip().upper() in ["TBD", "TO BE DETERMINED", "N/A", "NA", "NONE"]:
        return None
    
    # Remove any non-digits
    clean_code = "".join(c for c in str(code) if c.isdigit())
    
    return clean_code if clean_code else None


def get_parent_codes(code):
    """Get parent NAICS codes (2, 3, 4, 5 digit versions)."""
    if not code or len(code) < 2:
        return []
    
    parents = []
    for length in [2, 3, 4, 5]:
        if len(code) >= length:
            parents.append(code[:length])
    return parents


def analyze_naics_codes(export_csv=False):
    """Analyze all NAICS codes in the database."""
    app = create_app()
    
    with app.app_context():
        # Query all unique NAICS codes and their counts
        naics_query = (
            db.session.query(
                Prospect.naics,
                func.count(Prospect.id).label('count')
            )
            .filter(Prospect.naics.isnot(None))
            .group_by(Prospect.naics)
            .order_by(func.count(Prospect.id).desc())
            .all()
        )
        
        # Analyze codes
        total_codes = len(naics_query)
        total_prospects = sum(count for _, count in naics_query)
        
        codes_with_desc = []
        codes_missing_desc = []
        invalid_format_codes = []
        
        for naics_raw, count in naics_query:
            clean_code = clean_naics_code(naics_raw)
            
            if not clean_code:
                invalid_format_codes.append((naics_raw, count))
            elif len(clean_code) != 6:
                invalid_format_codes.append((naics_raw, count, f"Length: {len(clean_code)}"))
            else:
                description = get_naics_description(clean_code)
                if description:
                    codes_with_desc.append((clean_code, count, description))
                else:
                    codes_missing_desc.append((clean_code, count, naics_raw))
        
        # Print summary
        print("=" * 80)
        print("NAICS CODE ANALYSIS REPORT")
        print("=" * 80)
        print()
        
        print("SUMMARY STATISTICS:")
        print("-" * 40)
        print(f"Total unique NAICS codes in database: {total_codes}")
        print(f"Total prospects with NAICS codes: {total_prospects}")
        print(f"Codes in lookup table: {len(NAICS_DESCRIPTIONS)}")
        print()
        print(f"Codes with descriptions: {len(codes_with_desc)} ({len(codes_with_desc)/total_codes*100:.1f}%)")
        print(f"Codes missing descriptions: {len(codes_missing_desc)} ({len(codes_missing_desc)/total_codes*100:.1f}%)")
        print(f"Invalid format codes: {len(invalid_format_codes)} ({len(invalid_format_codes)/total_codes*100:.1f}%)")
        print()
        
        # Prospects affected
        prospects_with_desc = sum(count for _, count, _ in codes_with_desc)
        prospects_missing_desc = sum(count for _, count, _ in codes_missing_desc)
        prospects_invalid = sum(count for item in invalid_format_codes for count in [item[1]])
        
        print("PROSPECTS AFFECTED:")
        print("-" * 40)
        print(f"Prospects with valid descriptions: {prospects_with_desc} ({prospects_with_desc/total_prospects*100:.1f}%)")
        print(f"Prospects missing descriptions: {prospects_missing_desc} ({prospects_missing_desc/total_prospects*100:.1f}%)")
        print(f"Prospects with invalid codes: {prospects_invalid} ({prospects_invalid/total_prospects*100:.1f}%)")
        print()
        
        # Missing codes detail
        if codes_missing_desc:
            print("=" * 80)
            print("MISSING NAICS CODES (sorted by frequency):")
            print("=" * 80)
            print()
            print(f"{'Code':<10} {'Count':<10} {'Raw Value':<20} {'Possible Parent Codes'}")
            print("-" * 80)
            
            for clean_code, count, raw_value in codes_missing_desc[:50]:  # Show top 50
                parent_codes = get_parent_codes(clean_code)
                parent_info = []
                for parent in parent_codes:
                    # Check if any parent code pattern exists in our lookup
                    matching_codes = [k for k in NAICS_DESCRIPTIONS.keys() if k.startswith(parent)]
                    if matching_codes:
                        parent_info.append(f"{parent} ({len(matching_codes)} matches)")
                
                parent_str = ", ".join(parent_info) if parent_info else "No parent matches"
                print(f"{clean_code:<10} {count:<10} {raw_value:<20} {parent_str}")
            
            if len(codes_missing_desc) > 50:
                print(f"\n... and {len(codes_missing_desc) - 50} more missing codes")
        
        # Invalid format codes detail
        if invalid_format_codes:
            print()
            print("=" * 80)
            print("INVALID FORMAT CODES (sorted by frequency):")
            print("=" * 80)
            print()
            print(f"{'Raw Value':<30} {'Count':<10} {'Issue'}")
            print("-" * 80)
            
            for item in invalid_format_codes[:20]:  # Show top 20
                if len(item) == 3:
                    raw_value, count, issue = item
                    print(f"{str(raw_value):<30} {count:<10} {issue}")
                else:
                    raw_value, count = item
                    print(f"{str(raw_value):<30} {count:<10} Invalid/Empty")
            
            if len(invalid_format_codes) > 20:
                print(f"\n... and {len(invalid_format_codes) - 20} more invalid codes")
        
        # Export to CSV if requested
        if export_csv:
            import csv
            csv_file = "naics_analysis.csv"
            
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Type', 'Code', 'Raw Value', 'Count', 'Description/Issue'])
                
                for code, count, desc in codes_with_desc:
                    writer.writerow(['Valid', code, code, count, desc])
                
                for code, count, raw in codes_missing_desc:
                    writer.writerow(['Missing', code, raw, count, 'No description in lookup'])
                
                for item in invalid_format_codes:
                    if len(item) == 3:
                        raw, count, issue = item
                        writer.writerow(['Invalid', '', raw, count, issue])
                    else:
                        raw, count = item
                        writer.writerow(['Invalid', '', raw, count, 'Invalid/Empty'])
            
            print(f"\n✓ Analysis exported to {csv_file}")
        
        # Recommendations
        print()
        print("=" * 80)
        print("RECOMMENDATIONS:")
        print("=" * 80)
        print()
        
        if codes_missing_desc:
            # Find common prefixes in missing codes
            prefix_counter = Counter()
            for code, count, _ in codes_missing_desc:
                if len(code) >= 4:
                    prefix_counter[code[:4]] += count
            
            common_prefixes = prefix_counter.most_common(5)
            if common_prefixes:
                print("1. Most common missing code prefixes (4-digit):")
                for prefix, total_count in common_prefixes:
                    print(f"   - {prefix}xx: {total_count} prospects")
                print()
            
            print("2. Consider adding these missing codes to the NAICS_DESCRIPTIONS lookup table")
            print("   or implementing a fallback mechanism for non-standard codes.")
            print()
        
        if invalid_format_codes:
            print("3. Many invalid format codes detected. Consider:")
            print("   - Implementing better NAICS code validation during scraping")
            print("   - Creating cleanup scripts for existing data")
            print("   - Adding fuzzy matching for common typos")
        
        print()
        print("=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze NAICS codes to find missing descriptions"
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export analysis results to CSV file"
    )
    
    args = parser.parse_args()
    
    try:
        analyze_naics_codes(export_csv=args.export_csv)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()