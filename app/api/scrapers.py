import time

from flask import request

from app.api.factory import (
    api_route,
    create_blueprint,
    error_response,
    success_response,
)
from app.database import db
from app.database.models import DataSource, ScraperStatus
from app.exceptions import DatabaseError, NotFoundError, ScraperError
from app.utils.scraper_utils import (
    run_all_scrapers,
    trigger_scraper,
)

scrapers_bp, logger = create_blueprint("scrapers")


@api_route(scrapers_bp, "/<int:source_id>/pull", methods=["POST"], auth="super_admin")
def pull_data_source(source_id):
    """Trigger a data pull for a specific data source via ScraperService."""
    try:
        # Run the scraper synchronously for now
        result = trigger_scraper(source_id)

        # Return success with the result
        return success_response(
            data={
                "data_source_name": result.get("data_source_name"),
                "scraper_status": result.get("scraper_status", "completed"),
            },
            message=result.get("message", "Scraper completed")
        )
    except NotFoundError as nfe:
        raise nfe  # Re-raise to be handled by Flask error handlers
    except ScraperError as se:
        raise se  # Re-raise
    except DatabaseError as de:
        raise de  # Re-raise
    except Exception as e:
        # Catch any other unexpected errors that weren't caught by specific handlers
        logger.error(
            f"Route: Unexpected error for source ID {source_id}: {e}", exc_info=True
        )  # Use blueprint logger
        # Return a generic error response
        return error_response(500, "An unexpected error occurred during the scraper run")


@api_route(scrapers_bp, "/run-all", methods=["POST"], auth="super_admin")
def run_scrapers():
    """Trigger scrapers for all data sources."""
    try:
        results = run_all_scrapers()
        return success_response(
            data={"results": results},
            message=f"Scrapers completed for {len(results)} sources"
        )
    except Exception as e:
        logger.error(f"Error running all scrapers: {e}", exc_info=True)
        return error_response(500, "Failed to run scrapers")


@api_route(scrapers_bp, "/status", methods=["GET"], auth="admin")
def get_scrapers_status():
    """Get status of all scrapers."""
    try:
        # Get all scraper statuses
        statuses = db.session.query(ScraperStatus).all()
        status_dict = {s.source_id: s for s in statuses}

        # Get all data sources
        sources = db.session.query(DataSource).all()
        
        scraper_status = []
        for source in sources:
            status = status_dict.get(source.id)
            scraper_status.append({
                "source_id": source.id,
                "source_name": source.name,
                "description": source.description,
                "status": status.status if status else "unknown",
                "last_run": status.last_checked.isoformat() if status and status.last_checked else None,
                "records_found": status.records_found if status else 0,
                "error_message": status.error_message if status else None
            })
        
        return success_response(data={"scrapers": scraper_status})
    except Exception as e:
        logger.error(f"Error getting scraper status: {e}", exc_info=True)
        return error_response(500, "Failed to get scraper status")