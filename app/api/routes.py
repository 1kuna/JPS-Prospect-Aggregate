"""Routes for the API module."""

from flask import request, current_app, jsonify
from sqlalchemy import func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from app.api import api
from app.models import db, Prospect, DataSource, ScraperStatus
from app.exceptions import ValidationError, NotFoundError, DatabaseError, ScraperError
from app.utils.logger import logger
import math
import datetime
import os
import platform
import time
import traceback
import datetime
from app.core.scrapers.acquisition_gateway import AcquisitionGatewayScraper
from app.core.scrapers.ssa_scraper import SsaScraper

# Set up logging using the centralized utility
logger = logger.bind(name="api.routes")

def paginate_query(query, page, per_page):
    """Helper function to paginate query results."""
    # Validate pagination parameters
    try:
        page = int(page)
        if page < 1:
            raise ValidationError("Page number must be greater than or equal to 1")
    except ValueError:
        raise ValidationError("Page number must be an integer")
    
    try:
        per_page = int(per_page)
        if per_page < 1:
            raise ValidationError("Per page must be greater than or equal to 1")
        if per_page > 100:
            raise ValidationError("Per page cannot exceed 100")
    except ValueError:
        raise ValidationError("Per page must be an integer")
    
    # Calculate pagination offsets
    offset = (page - 1) * per_page
    
    # Calculate total items and pages
    total_items = query.count()
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    
    # Apply pagination to query
    paginated_query = query.offset(offset).limit(per_page)
    
    # Create pagination info
    pagination = {
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }
    
    return paginated_query, pagination


@api.route('/proposals', methods=['GET'])
def get_proposals():
    """Get all proposals with pagination and filtering."""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 100)
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'desc')
        search_term = request.args.get('search', '')
        
        session = db.session
        # Build base query
        query = session.query(Prospect)
        
        # Apply search filter if provided
        if search_term:
            search_filter = (
                (Prospect.title.ilike(f'%{search_term}%')) |
                (Prospect.description.ilike(f'%{search_term}%')) |
                (Prospect.agency.ilike(f'%{search_term}%'))
            )
            query = query.filter(search_filter)
        
        # Apply sorting
        sort_column = getattr(Prospect, sort_by, Prospect.id)
        if sort_order == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        prospects_data = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Convert to dictionary
        prospects_dict = [p.to_dict() for p in prospects_data]
        
        return jsonify({
            'proposals': prospects_dict,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': math.ceil(total_count / per_page)
        })
            
    except ValueError as e:
        raise ValidationError(f"Invalid parameter: {str(e)}")
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        db.session.rollback()
        raise


@api.route('/proposals/<string:prospect_id>', methods=['GET'])
def get_proposal(prospect_id):
    """Get a specific prospect by ID."""
    session = db.session
    prospect = session.query(Prospect).get(prospect_id)
    if not prospect:
        raise NotFoundError(f"Prospect with ID {prospect_id} not found")
    return jsonify(prospect.to_dict())


@api.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint."""
    try:
        session = db.session
        # Simple database query to check connection
        session.query(DataSource).first()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'error': str(e)
        }), 500


@api.route('/dashboard')
def get_dashboard():
    """Get dashboard summary information."""
    session = db.session
    try:
        # Get total number of prospects
        total_prospects = session.query(func.count(Prospect.id)).scalar()
        
        # Get newest data source update
        latest_update = session.query(func.max(DataSource.last_scraped)).scalar()
        
        # Get top agencies by prospect count
        top_agencies = session.query(
            Prospect.agency,
            func.count(Prospect.id).label('prospect_count')
        ).group_by(Prospect.agency).order_by(desc('prospect_count')).limit(5).all()
        
        # Get upcoming prospects (using release_date)
        today = datetime.datetime.now().date()
        upcoming_prospects = session.query(Prospect).filter(
            Prospect.release_date >= today
        ).order_by(Prospect.release_date).limit(5).all()
        
        return jsonify({
            "status": "success",
            "data": {
                "total_proposals": total_prospects,
                "latest_update": latest_update.isoformat() if latest_update else None,
                "top_agencies": [{"agency": agency, "count": count} for agency, count in top_agencies],
                "upcoming_proposals": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "agency": p.agency,
                        "proposal_date": p.release_date.isoformat() if p.release_date else None
                    } for p in upcoming_prospects
                ]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error in get_dashboard: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500


@api.route('/data-sources', methods=['GET'])
def get_data_sources():
    """Get all data sources."""
    session = db.session
    try:
        sources = session.query(DataSource).all()
        result = []
        
        for source in sources:
            # Count prospects for this source
            prospect_count = session.query(func.count(Prospect.id)).filter(Prospect.source_id == source.id).scalar()
            
            # Get the latest status check if available
            status_record = session.query(ScraperStatus).filter_by(source_id=source.id).order_by(ScraperStatus.last_checked.desc()).first()
            
            result.append({
                "id": source.id,
                "name": source.name,
                "url": source.url,
                "description": source.description,
                "last_scraped": source.last_scraped.isoformat() if source.last_scraped else None,
                "proposalCount": prospect_count,
                "last_checked": status_record.last_checked.isoformat() if status_record and status_record.last_checked else None,
                "status": status_record.status if status_record else "unknown"
            })
        
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        current_app.logger.error(f"Error in get_data_sources: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/data-sources/<int:source_id>', methods=['PUT'])
def update_data_source(source_id):
    """Update a data source."""
    session = db.session
    try:
        # Validate input
        data = request.json
        if not data:
            raise ValidationError("No data provided")
        
        # Define updatable fields and their types/validation
        updatable_fields = {
            'name': str,
            'url': str,
            'description': str,
            'frequency': ['daily', 'weekly', 'monthly', 'manual', None] # None allows clearing
        }

        source = session.query(DataSource).filter(DataSource.id == source_id).first()
        if not source:
            raise NotFoundError(f"Data source with ID {source_id} not found")

        for field, value in data.items():
            if field in updatable_fields:
                if field == 'frequency' and value is not None and value not in updatable_fields['frequency']:
                    raise ValidationError(f"Invalid frequency. Must be one of: {', '.join(f for f in updatable_fields['frequency'] if f is not None)}")
                setattr(source, field, value)
            else:
                logger.warning(f"Attempted to update non-allowed field: {field}")
        
        session.commit()
        return jsonify({"status": "success", "message": "Data source updated", "data": source.to_dict()})
    except ValidationError as ve:
        db.session.rollback()
        raise ve
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in update_data_source: {str(e)}")
        raise DatabaseError("Failed to update data source")


@api.route('/data-sources', methods=['POST'])
def create_data_source():
    """Create a new data source."""
    session = db.session
    try:
        data = request.json
        if not data:
            raise ValidationError("No data provided for creating data source.")

        name = data.get('name')
        url = data.get('url')
        description = data.get('description')
        frequency = data.get('frequency', 'manual') # Default frequency to 'manual'

        if not name:
            raise ValidationError("Name is required for data source.")
        
        valid_frequencies = ['daily', 'weekly', 'monthly', 'manual']
        if frequency not in valid_frequencies:
            raise ValidationError(f"Invalid frequency. Must be one of: {', '.join(valid_frequencies)}")

        existing_source = session.query(DataSource).filter_by(name=name).first()
        if existing_source:
            raise ValidationError(f"Data source with name '{name}' already exists.")

        new_source = DataSource(
            name=name,
            url=url,
            description=description,
            frequency=frequency
        )
        session.add(new_source)
        session.commit()
        
        # Create an initial status record
        initial_status = ScraperStatus(
            source_id=new_source.id,
            status='pending', # Initial status
            details='Newly created data source, awaiting first scrape.'
        )
        session.add(initial_status)
        session.commit()

        return jsonify({"status": "success", "message": "Data source created", "data": new_source.to_dict()}), 201
    except ValidationError as ve:
        db.session.rollback()
        raise ve
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating data source: {e}", exc_info=True)
        raise DatabaseError("Could not create data source")


@api.route('/data-sources/<int:source_id>', methods=['DELETE'])
def delete_data_source(source_id):
    """Delete a data source and its related prospects and status records."""
    session = db.session
    try:
        source = session.query(DataSource).filter(DataSource.id == source_id).first()
        if not source:
            raise NotFoundError(f"Data source with ID {source_id} not found")

        # Manually delete related prospects if cascade is not working as expected or for logging
        # prospects_to_delete = session.query(Prospect).filter(Prospect.source_id == source_id).all()
        # for prop in prospects_to_delete:
        #     session.delete(prop)
        # logger.info(f"Deleted {len(prospects_to_delete)} prospects for source ID {source_id}")
        
        # Relationships `prospects` and `status_records` have cascade="all, delete-orphan"
        session.delete(source)
        session.commit()
        return jsonify({"status": "success", "message": f"Data source {source_id} and related data deleted"})
    except NotFoundError as nfe:
        db.session.rollback()
        raise nfe
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting data source {source_id}: {e}", exc_info=True)
        raise DatabaseError(f"Could not delete data source {source_id}")


@api.route('/data-sources/<int:source_id>/pull', methods=['POST'])
def pull_data_source(source_id):
    """Trigger a data pull for a specific data source."""
    session = db.session
    try:
        data_source = session.query(DataSource).filter_by(id=source_id).first()
        if not data_source:
            raise NotFoundError(f"Data source with ID {source_id} not found.")

        scraper_instance = None
        scraper_name_map = {
            "Acquisition Gateway": AcquisitionGatewayScraper,
            "SSA Forecast": SsaScraper,
            # Add other scrapers here
        }
        
        ScraperClass = scraper_name_map.get(data_source.name)
        if not ScraperClass:
            raise ScraperError(f"No scraper configured for data source: {data_source.name}")

        scraper_instance = ScraperClass()
        
        # Update status to 'working' before starting
        status_record = session.query(ScraperStatus).filter_by(source_id=source_id).order_by(ScraperStatus.last_checked.desc()).first()
        if not status_record: # Should have been created with data source
            status_record = ScraperStatus(source_id=source_id, status='pending', details='Status record created on first pull trigger.')
            session.add(status_record)

        status_record.status = 'working'
        status_record.last_checked = datetime.datetime.utcnow()
        status_record.details = "Scrape process initiated."
        session.commit()

        try:
            logger.info(f"Starting scrape for {data_source.name} (ID: {source_id})")
            # Run the scraper (this might be a long-running task; consider background tasks for real apps)
            # For simplicity, running it synchronously here.
            scraper_instance.run() 
            
            status_record.status = 'completed'
            status_record.details = f"Scrape completed successfully at {datetime.datetime.utcnow().isoformat()}."
            data_source.last_scraped = datetime.datetime.utcnow() # Update last_scraped on successful completion
            logger.info(f"Scrape for {data_source.name} completed successfully.")

        except Exception as scrape_exc:
            logger.error(f"Scraper for {data_source.name} failed: {scrape_exc}", exc_info=True)
            status_record.status = 'failed'
            status_record.details = f"Scrape failed: {str(scrape_exc)[:500]}" # Truncate long errors
            # Do not update data_source.last_scraped on failure
            raise ScraperError(f"Scraping {data_source.name} failed: {scrape_exc}")
        finally:
            status_record.last_checked = datetime.datetime.utcnow()
            session.commit()

        return jsonify({"status": "success", "message": f"Data pull for {data_source.name} initiated successfully. Final status: {status_record.status}"})

    except NotFoundError as nfe:
        db.session.rollback()
        raise nfe
    except ScraperError as se:
        # db.session.commit() # Commit status changes even if scraper fails
        db.session.rollback() # Rollback to ensure consistent state if commit in finally failed or not reached.
                              # The state of status_record might be inconsistent if an error occurs *during* its update.
                              # Better to rely on the commit in finally.
        current_app.logger.error(f"Scraper error during pull for source ID {source_id}: {se}", exc_info=True)
        # Re-raise to be caught by error handler
        raise se
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error during pull for source ID {source_id}: {e}", exc_info=True)
        # Update status to 'failed' if not already handled by ScraperError
        if 'status_record' in locals() and status_record:
            try:
                status_record.status = 'failed'
                status_record.details = f"Pull process failed unexpectedly: {str(e)[:500]}"
                status_record.last_checked = datetime.datetime.utcnow()
                session.commit() # Attempt to commit this final status
            except Exception as final_commit_e:
                current_app.logger.error(f"Failed to commit final error status for source ID {source_id}: {final_commit_e}", exc_info=True)
                db.session.rollback() # Rollback this attempt
        raise DatabaseError(f"Unexpected error processing pull for {data_source.name if 'data_source' in locals() and data_source else source_id}")


@api.route('/data-sources/<int:source_id>/status', methods=['GET'])
def check_scraper_status(source_id):
    """Check the status of a scraper for a given data source."""
    session = db.session
    try:
        data_source = session.query(DataSource).filter_by(id=source_id).first()
        if not data_source:
            raise NotFoundError(f"Data source with ID {source_id} not found.")

        # Get the most recent status record
        status_record = session.query(ScraperStatus).filter_by(source_id=source_id).order_by(ScraperStatus.last_checked.desc()).first()

        if not status_record:
            return jsonify({
                "status": "success", # Or "nodata" ?
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
        # db.session.rollback() # Not needed for GET
        raise nfe
    except Exception as e:
        # db.session.rollback() # Not needed for GET
        current_app.logger.error(f"Error checking scraper status for source ID {source_id}: {e}", exc_info=True)
        raise DatabaseError(f"Could not retrieve status for data source {source_id}") 