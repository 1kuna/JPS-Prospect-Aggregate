#!/usr/bin/env python3
"""Backfill NAICS Descriptions Script

This script backfills missing NAICS descriptions for prospects that have NAICS codes
but no descriptions. Uses the official NAICS lookup table to ensure standardized,
accurate descriptions.

Usage:
    python scripts/backfill_naics_descriptions.py [--dry-run] [--limit N]

Options:
    --dry-run    Show what would be updated without making changes
    --limit N    Process only N prospects (for testing)
"""

import argparse
import os
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database.models import Prospect
from app.services.llm_service import LLMService
from app.utils.naics_lookup import get_naics_description, validate_naics_code


def get_prospects_needing_descriptions(limit=None):
    """Get prospects that have NAICS codes but no descriptions"""
    query = Prospect.query.filter(
        Prospect.naics.isnot(None), Prospect.naics_description.is_(None)
    )

    if limit:
        query = query.limit(limit)

    return query.all()


def analyze_naics_coverage():
    """Analyze current NAICS coverage in the database"""
    total_prospects = Prospect.query.count()

    prospects_with_naics = Prospect.query.filter(Prospect.naics.isnot(None)).count()

    prospects_with_descriptions = Prospect.query.filter(
        Prospect.naics.isnot(None), Prospect.naics_description.isnot(None)
    ).count()

    prospects_needing_descriptions = Prospect.query.filter(
        Prospect.naics.isnot(None), Prospect.naics_description.is_(None)
    ).count()

    return {
        "total_prospects": total_prospects,
        "prospects_with_naics": prospects_with_naics,
        "prospects_with_descriptions": prospects_with_descriptions,
        "prospects_needing_descriptions": prospects_needing_descriptions,
    }


def preview_backfill(prospects):
    """Preview what would be backfilled"""
    print(f"\\nPREVIEW: {len(prospects)} prospects would be updated:\\n")

    code_counts = {}
    valid_codes = 0
    invalid_codes = 0

    for prospect in prospects:
        naics_code = prospect.naics

        if validate_naics_code(naics_code):
            description = get_naics_description(naics_code)
            if description:
                code_counts[naics_code] = code_counts.get(naics_code, 0) + 1
                valid_codes += 1
            else:
                invalid_codes += 1
                print(f"  ❌ {naics_code}: No description available")
        else:
            invalid_codes += 1
            print(f"  ❌ {naics_code}: Invalid code format")

    print(f"Valid codes that can be backfilled: {valid_codes}")
    print(f"Invalid/unsupported codes: {invalid_codes}")

    if code_counts:
        print("\\nTop NAICS codes to be backfilled:")
        sorted_codes = sorted(code_counts.items(), key=lambda x: x[1], reverse=True)
        for code, count in sorted_codes[:10]:
            description = get_naics_description(code)
            print(f"  {code}: {description} ({count} prospects)")


def main():
    parser = argparse.ArgumentParser(description="Backfill NAICS descriptions")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of prospects to process"
    )
    parser.add_argument(
        "--yes", action="store_true", help="Auto-confirm without prompting"
    )

    args = parser.parse_args()

    # Initialize Flask app and database
    app = create_app()

    with app.app_context():
        print("NAICS Description Backfill Script")
        print("=" * 40)

        # Analyze current coverage
        print("\\nAnalyzing current NAICS coverage...")
        coverage = analyze_naics_coverage()

        print(f"Total prospects: {coverage['total_prospects']:,}")
        print(f"Prospects with NAICS codes: {coverage['prospects_with_naics']:,}")
        print(
            f"Prospects with descriptions: {coverage['prospects_with_descriptions']:,}"
        )
        print(
            f"Prospects needing descriptions: {coverage['prospects_needing_descriptions']:,}"
        )

        if coverage["prospects_needing_descriptions"] == 0:
            print("\\n✅ All prospects with NAICS codes already have descriptions!")
            return

        # Get prospects needing descriptions
        prospects = get_prospects_needing_descriptions(args.limit)

        if not prospects:
            print("\\n✅ No prospects found needing description backfill!")
            return

        # Preview what would be changed
        preview_backfill(prospects)

        if args.dry_run:
            print("\\n🔍 DRY RUN: No changes were made")
            return

        # Confirm before proceeding
        if not args.yes:
            confirm = input(
                f"\\n❓ Proceed with backfilling {len(prospects)} prospects? (y/N): "
            )
            if confirm.lower() != "y":
                print("❌ Operation cancelled")
                return

        # Perform backfill
        print("\\n🔄 Starting backfill process...")
        start_time = datetime.now()

        llm_service = LLMService()
        backfilled_count = llm_service.backfill_naics_descriptions(prospects)

        end_time = datetime.now()
        duration = end_time - start_time

        print("\\n✅ Backfill complete!")
        print(f"   • Processed: {len(prospects)} prospects")
        print(f"   • Backfilled: {backfilled_count} descriptions")
        print(f"   • Duration: {duration.total_seconds():.1f} seconds")

        # Final coverage analysis
        print("\\n📊 Final coverage analysis:")
        final_coverage = analyze_naics_coverage()
        print(
            f"   • Prospects with descriptions: {final_coverage['prospects_with_descriptions']:,}"
        )
        print(
            f"   • Prospects still needing descriptions: {final_coverage['prospects_needing_descriptions']:,}"
        )

        if final_coverage["prospects_needing_descriptions"] == 0:
            print("\\n🎉 All prospects with NAICS codes now have descriptions!")


if __name__ == "__main__":
    main()
