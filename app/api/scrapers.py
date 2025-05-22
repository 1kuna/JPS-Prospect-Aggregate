from flask import Blueprint, jsonify, current_app
from app.models import db, DataSource, ScraperStatus
from app.exceptions import NotFoundError, ScraperError, DatabaseError
from app.utils.logger import logger
from app.services.scraper_service import ScraperService
import threading

scrapers_bp = Blueprint('scrapers', __name__)

# Set up logging using the centralized utility
logger = logger.bind(name="api.scrapers")

@scrapers_bp.route('/<int:source_id>/pull', methods=['POST'])
def pull_data_source(source_id):
    """Trigger a data pull for a specific data source via ScraperService."""
    try:
        # Run the scraper in a background thread
        thread = threading.Thread(target=ScraperService.trigger_scrape, args=(source_id,))
        thread.start()

        # Return 202 Accepted with a status message
        status_url = f"/api/scrapers/status/{source_id}" # Example status URL
        return jsonify({
            "status": "accepted",
            "message": f"Data pull for source ID {source_id} initiated. Check status at {status_url}",
            "status_url": status_url
        }), 202 # HTTP 202 Accepted for async operations
    except NotFoundError as nfe:
        raise nfe # Re-raise to be handled by Flask error handlers
    except ScraperError as se:
        raise se # Re-raise
    except DatabaseError as de:
        raise de # Re-raise
    except Exception as e:
        # Catch any other unexpected errors that weren't caught by specific handlers
        logger.error(f"Route: Unexpected error for source ID {source_id}: {e}", exc_info=True) # Use blueprint logger
        # Return a generic error response
        return jsonify({
            "status": "error", 
            "message": f"An unexpected error occurred while processing the request for source ID {source_id}."
        }), 500

@scrapers_bp.route('/<int:source_id>/status', methods=['GET'])
def check_scraper_status(source_id):
    """Check the status of a scraper for a given data source."""
    session = db.session
    try:
        data_source = session.query(DataSource).filter_by(id=source_id).first()
        if not data_source:
            raise NotFoundError(f"Data source with ID {source_id} not found.")

        status_record = session.query(ScraperStatus).filter_by(source_id=source_id).order_by(ScraperStatus.last_checked.desc()).first()

        if not status_record:
            return jsonify({
                "status": "success", 
                "data_source_name": data_source.name,
                "scraper_status": "unknown",
                "last_checked": None,
                "details": "No status records found for this data source."
            })

        return jsonify({
            "status": "success",
            "data_source_name": data_source.name,
            "scraper_status": status_record.status,
            "last_checked": status_record.last_checked.isoformat() if status_record.last_checked else None,
            "details": status_record.details
        })
    except NotFoundError as nfe:
        raise nfe
    except Exception as e:
        logger.error(f"Error checking scraper status for source ID {source_id}: {e}", exc_info=True)
        raise DatabaseError(f"Could not retrieve status for data source {source_id}") 