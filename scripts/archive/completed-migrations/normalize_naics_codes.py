#!/usr/bin/env python3
"""Script to normalize existing NAICS codes in the database."""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy import func

from app import create_app
from app.database import db
from app.database.models import Prospect
from app.utils.logger import logger
from app.utils.value_and_date_parsing import normalize_naics_code


def main():
    """Normalize all NAICS codes in the database."""
    app = create_app()

    with app.app_context():
        logger.info("Fetching prospects with NAICS codes...")

        # Get all prospects with non-null NAICS codes
        prospects = (
            db.session.query(Prospect)
            .filter(Prospect.naics.isnot(None), Prospect.naics != "")
            .all()
        )

        logger.info(f"Found {len(prospects)} prospects with NAICS codes")

        # Track statistics
        stats = {
            "total": len(prospects),
            "normalized": 0,
            "already_clean": 0,
            "invalidated": 0,
        }

        # Process each prospect
        for prospect in prospects:
            original_naics = prospect.naics
            normalized_naics = normalize_naics_code(original_naics)

            # Convert pd.NA to None for database
            if pd.isna(normalized_naics):
                normalized_naics = None

            if normalized_naics != original_naics:
                if normalized_naics is None:
                    stats["invalidated"] += 1
                    logger.info(
                        f"Invalid NAICS code cleared: '{original_naics}' -> None"
                    )
                else:
                    stats["normalized"] += 1
                    logger.info(
                        f"Normalized: '{original_naics}' -> '{normalized_naics}'"
                    )

                prospect.naics = normalized_naics
            else:
                stats["already_clean"] += 1

        # Commit changes
        if stats["normalized"] > 0 or stats["invalidated"] > 0:
            logger.info("\nCommitting changes to database...")
            db.session.commit()
            logger.success("Changes committed successfully!")
        else:
            logger.info("\nNo changes needed.")

        # Print summary
        logger.info("\n" + "=" * 50)
        logger.info("SUMMARY:")
        logger.info(f"Total prospects processed: {stats['total']}")
        logger.info(f"NAICS codes normalized: {stats['normalized']}")
        logger.info(f"Invalid codes cleared: {stats['invalidated']}")
        logger.info(f"Already clean: {stats['already_clean']}")

        # Show sample of current NAICS codes
        logger.info("\n" + "=" * 50)
        logger.info("Sample of current NAICS codes in database:")
        sample_query = (
            db.session.query(Prospect.naics, func.count(Prospect.id).label("count"))
            .filter(Prospect.naics.isnot(None))
            .group_by(Prospect.naics)
            .order_by(func.count(Prospect.id).desc())
            .limit(10)
        )

        for naics, count in sample_query:
            logger.info(f"  {naics}: {count} records")


if __name__ == "__main__":
    main()
