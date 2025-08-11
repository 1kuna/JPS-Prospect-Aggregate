"""Ensure all data sources exist in the database.
This utility is called on app startup to guarantee all scrapers have their data sources.
"""

from app.database import db
from app.database.models import DataSource, ScraperStatus
from app.utils.logger import logger

# Define all data sources that should exist
ALL_DATA_SOURCES = [
    {
        "name": "Acquisition Gateway",
        "scraper_key": "ACQGW",
        "url": "https://hallways.cap.gsa.gov/app/#/gateway/acquisition-gateway/forecast-documents",
        "description": "GSA Acquisition Gateway forecast documents",
        "frequency": "weekly",
    },
    {
        "name": "Department of Commerce",
        "scraper_key": "DOC",
        "url": "https://www.commerce.gov/",
        "description": "Department of Commerce procurement forecasts",
        "frequency": "weekly",
    },
    {
        "name": "Department of Homeland Security",
        "scraper_key": "DHS",
        "url": "https://www.dhs.gov/",
        "description": "DHS procurement forecasts",
        "frequency": "weekly",
    },
    {
        "name": "Department of Justice",
        "scraper_key": "DOJ",
        "url": "https://www.justice.gov/",
        "description": "DOJ procurement forecasts",
        "frequency": "weekly",
    },
    {
        "name": "Department of State",
        "scraper_key": "DOS",
        "url": "https://www.state.gov/",
        "description": "DOS procurement forecasts",
        "frequency": "weekly",
    },
    {
        "name": "Department of Transportation",
        "scraper_key": "DOT",
        "url": "https://www.transportation.gov/",
        "description": "DOT procurement forecasts",
        "frequency": "weekly",
    },
    {
        "name": "Health and Human Services",
        "scraper_key": "HHS",
        "url": "https://www.hhs.gov/",
        "description": "HHS procurement forecasts",
        "frequency": "weekly",
    },
    {
        "name": "Social Security Administration",
        "scraper_key": "SSA",
        "url": "https://www.ssa.gov/",
        "description": "SSA procurement forecasts",
        "frequency": "weekly",
    },
    {
        "name": "Department of Treasury",
        "scraper_key": "TREAS",
        "url": "https://www.treasury.gov/",
        "description": "Treasury procurement forecasts",
        "frequency": "weekly",
    },
]


def ensure_all_data_sources_exist():
    """Ensure all data sources exist in the database.
    Creates any missing sources and updates scraper_key if needed.

    Returns:
        int: Number of data sources created or updated
    """
    try:
        created_count = 0
        updated_count = 0

        for source_data in ALL_DATA_SOURCES:
            # Check if source already exists
            existing = DataSource.query.filter_by(name=source_data["name"]).first()

            if existing:
                # Update scraper_key if missing
                if not existing.scraper_key:
                    existing.scraper_key = source_data["scraper_key"]
                    db.session.commit()
                    updated_count += 1
                    logger.info(f"Updated scraper_key for {source_data['name']}")
            else:
                # Create new data source
                new_source = DataSource(
                    name=source_data["name"],
                    scraper_key=source_data["scraper_key"],
                    url=source_data["url"],
                    description=source_data["description"],
                    frequency=source_data["frequency"],
                )
                db.session.add(new_source)
                db.session.flush()  # Get the ID

                # Create initial status
                initial_status = ScraperStatus(
                    source_id=new_source.id,
                    status="pending",
                    details="Newly created data source, awaiting first scrape.",
                )
                db.session.add(initial_status)

                created_count += 1
                logger.info(f"Created data source: {source_data['name']}")

        # Commit all changes
        if created_count > 0 or updated_count > 0:
            db.session.commit()
            logger.info(
                f"Data sources check complete: {created_count} created, {updated_count} updated"
            )

        return created_count + updated_count

    except Exception as e:
        logger.error(f"Error ensuring data sources exist: {e}")
        db.session.rollback()
        return 0
