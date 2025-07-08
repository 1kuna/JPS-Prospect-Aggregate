from flask import Blueprint, jsonify
from app.database import db
from app.database.models import DataSource, ScraperStatus
from app.exceptions import NotFoundError, ScraperError, DatabaseError
from app.utils.logger import logger
from app.services.scraper_service import ScraperService
from app.api.auth import admin_required
import threading
import time

scrapers_bp = Blueprint('scrapers', __name__)

# Set up logging using the centralized utility
logger = logger.bind(name="api.scrapers")

@scrapers_bp.route('/<int:source_id>/pull', methods=['POST'])
@admin_required
def pull_data_source(source_id):
    """Trigger a data pull for a specific data source via ScraperService."""
    try:
        # Run the scraper synchronously for now
        result = ScraperService.trigger_scrape(source_id)
        
        # Return success with the result
        return jsonify({
            "status": "success",
            "message": result.get("message", "Scraper completed"),
            "data_source_name": result.get("data_source_name"),
            "scraper_status": result.get("scraper_status", "completed")
        }), 200
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
@admin_required
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

@scrapers_bp.route('/run-all', methods=['POST'])
@admin_required
def run_all_scrapers():
    """Run all scrapers synchronously in order."""
    try:
        # Get all data sources with scraper keys
        session = db.session
        data_sources = session.query(DataSource).filter(
            DataSource.scraper_key.isnot(None)
        ).all()
        
        if not data_sources:
            return jsonify({
                "status": "error",
                "message": "No data sources with configured scrapers found"
            }), 404
        
        results = []
        total_started = time.time()
        
        # Run each scraper synchronously
        for source in data_sources:
            logger.info(f"Starting scraper for {source.name} (ID: {source.id})")
            start_time = time.time()
            
            try:
                result = ScraperService.trigger_scrape(source.id)
                duration = time.time() - start_time
                results.append({
                    "source_name": source.name,
                    "source_id": source.id,
                    "status": "success",
                    "duration": round(duration, 2),
                    "message": result.get("message", "Completed successfully")
                })
                logger.info(f"Completed scraper for {source.name} in {duration:.2f}s")
            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                results.append({
                    "source_name": source.name,
                    "source_id": source.id,
                    "status": "failed",
                    "duration": round(duration, 2),
                    "error": error_msg
                })
                logger.error(f"Failed scraper for {source.name} after {duration:.2f}s: {error_msg}")
        
        total_duration = time.time() - total_started
        success_count = sum(1 for r in results if r["status"] == "success")
        
        return jsonify({
            "status": "success",
            "message": f"Ran {len(data_sources)} scrapers: {success_count} succeeded, {len(data_sources) - success_count} failed",
            "total_duration": round(total_duration, 2),
            "results": results
        }), 200
        
    except Exception as e:
        logger.error(f"Error running all scrapers: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to run all scrapers: {str(e)}"
        }), 500 