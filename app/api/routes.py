"""Routes for the API module."""

from flask import request, current_app, jsonify
from sqlalchemy import func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from app.api import api
from app.models import Proposal, DataSource, ScraperStatus
from app.exceptions import ValidationError, NotFoundError, DatabaseError, ScraperError
from app.utils.logger import logger
from app.database.connection import get_db as db_session
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
        
        with db_session() as session:
            # Build base query
            query = session.query(Proposal)
            
            # Apply search filter if provided
            if search_term:
                search_filter = (
                    (Proposal.title.ilike(f'%{search_term}%')) |
                    (Proposal.description.ilike(f'%{search_term}%')) |
                    (Proposal.agency.ilike(f'%{search_term}%'))
                )
                query = query.filter(search_filter)
            
            # Apply sorting
            sort_column = getattr(Proposal, sort_by, Proposal.id)
            if sort_order == 'desc':
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
            
            # Get total count for pagination
            total_count = query.count()
            
            # Apply pagination
            proposals = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Convert to dictionary
            proposals_dict = [proposal.to_dict() for proposal in proposals]
            
            return jsonify({
                'proposals': proposals_dict,
                'total': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': math.ceil(total_count / per_page)
            })
            
    except ValueError as e:
        raise ValidationError(f"Invalid parameter: {str(e)}")
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise


@api.route('/proposals/<int:proposal_id>', methods=['GET'])
def get_proposal(proposal_id):
    """Get a specific proposal by ID."""
    with db_session() as session:
        proposal = session.query(Proposal).get(proposal_id)
        if not proposal:
            raise NotFoundError(f"Proposal with ID {proposal_id} not found")
        return jsonify(proposal.to_dict())


@api.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint."""
    try:
        with db_session() as session:
            # Simple database query to check connection
            session.query(DataSource).first()
            
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'error': str(e)
        }), 500


@api.route('/dashboard')
def get_dashboard():
    """Get dashboard summary information."""
    with db_session() as session:
        try:
            # Get total number of proposals
            total_proposals = session.query(func.count(Proposal.id)).scalar()
            
            # Get newest data source update
            latest_update = session.query(func.max(DataSource.last_scraped)).scalar()
            
            # Get top agencies by proposal count
            top_agencies = session.query(
                Proposal.agency,
                func.count(Proposal.id).label('proposal_count')
            ).group_by(Proposal.agency).order_by(desc('proposal_count')).limit(5).all()
            
            # Get upcoming proposals (using release_date)
            today = datetime.datetime.now().date()
            upcoming_proposals = session.query(Proposal).filter(
                Proposal.release_date >= today # Changed from proposal_date
            ).order_by(Proposal.release_date).limit(5).all() # Changed from proposal_date
            
            return jsonify({
                "status": "success",
                "data": {
                    "total_proposals": total_proposals,
                    "latest_update": latest_update.isoformat() if latest_update else None,
                    "top_agencies": [{"agency": agency, "count": count} for agency, count in top_agencies],
                    "upcoming_proposals": [
                        {
                            "id": p.id,
                            "title": p.title,
                            "agency": p.agency,
                            "proposal_date": p.release_date.isoformat() if p.release_date else None # Changed from proposal_date
                        } for p in upcoming_proposals
                    ]
                }
            })
        except Exception as e:
            current_app.logger.error(f"Error in get_dashboard: {str(e)}")
            return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500


@api.route('/data-sources', methods=['GET'])
def get_data_sources():
    """Get all data sources."""
    with db_session() as session:
        try:
            sources = session.query(DataSource).all()
            result = []
            
            for source in sources:
                # Count proposals for this source
                proposal_count = session.query(func.count(Proposal.id)).filter(Proposal.source_id == source.id).scalar()
                
                # Get the latest status check if available
                status_record = session.query(ScraperStatus).filter_by(source_id=source.id).first()
                
                result.append({
                    "id": source.id,
                    "name": source.name,
                    "url": source.url,
                    "description": source.description,
                    "last_scraped": source.last_scraped.isoformat() if source.last_scraped else None,
                    "proposalCount": proposal_count,
                    "last_checked": status_record.last_checked.isoformat() if status_record and status_record.last_checked else None,
                    "status": status_record.status if status_record else "unknown"
                })
            
            return jsonify({"status": "success", "data": result})
        except Exception as e:
            current_app.logger.error(f"Error in get_data_sources: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/data-sources/<int:source_id>', methods=['PUT'])
def update_data_source(source_id):
    """Update a data source."""
    with db_session() as session:
        try:
            # Validate input
            data = request.json
            if not data:
                raise ValidationError("No data provided")
            
            required_fields = ['name', 'url', 'frequency']
            for field in required_fields:
                if field not in data:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Validate frequency
            valid_frequencies = ['daily', 'weekly', 'monthly', 'manual']
            if data['frequency'] not in valid_frequencies:
                raise ValidationError(f"Invalid frequency. Must be one of: {', '.join(valid_frequencies)}")
            
            # Update data source
            source = session.query(DataSource).filter(DataSource.id == source_id).first()
            if not source:
                raise NotFoundError(f"Data source with ID {source_id} not found")
            
            # Update fields
            source.name = data['name']
            source.url = data['url']
            source.frequency = data['frequency']
            if 'description' in data:
                source.description = data['description']
            if 'active' in data:
                source.active = data['active']
            
            # Additional fields
            if 'settings' in data:
                source.settings = data['settings']
            if 'credentials' in data:
                source.credentials = data['credentials']
            
            # Update timestamps
            source.updated_at = datetime.datetime.utcnow()
            
            # Commit changes
            session.add(source)
        
            return jsonify({"status": "success", "message": f"Data source {source_id} updated successfully"}), 200
        except ValidationError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except NotFoundError as e:
            return jsonify({"status": "error", "message": str(e)}), 404
        except Exception as e:
            logger.error(f"Error updating data source: {str(e)}")
            return jsonify({"status": "error", "message": "An error occurred while updating the data source"}), 500


@api.route('/data-sources', methods=['POST'])
def create_data_source():
    """Create a new data source."""
    with db_session() as session:
        try:
            # Get request data
            data = request.json
            if not data:
                raise ValidationError("No data provided")
            
            # Validate required fields
            if 'name' not in data or not data['name']:
                raise ValidationError("Name is required")
            if 'url' not in data or not data['url']:
                raise ValidationError("URL is required")
            
            # Create new data source
            source = DataSource(
                name=data['name'],
                url=data['url'],
                description=data.get('description', '')
            )
            
            # Add to session and commit
            session.add(source)
            session.flush()  # Flush to get the ID
            
            return jsonify({
                "status": "success",
                "data": {
                    "id": source.id,
                    "name": source.name,
                    "url": source.url,
                    "description": source.description
                }
            }), 201
        except ValidationError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            current_app.logger.error(f"Error in create_data_source: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/data-sources/<int:source_id>', methods=['DELETE'])
def delete_data_source(source_id):
    """Delete a data source."""
    with db_session() as session:
        try:
            # Find the data source
            source = session.query(DataSource).filter_by(id=source_id).first()
            if not source:
                raise NotFoundError(f"Data source with ID {source_id} not found")
            
            # Check if there are proposals associated with this source
            proposal_count = session.query(func.count(Proposal.id)).filter(Proposal.source_id == source_id).scalar()
            if proposal_count > 0:
                raise ValidationError(f"Cannot delete data source with {proposal_count} associated proposals. Delete the proposals first.")
            
            # Delete the source
            session.delete(source)
            session.commit()
            
            return jsonify({
                "status": "success",
                "message": f"Data source with ID {source_id} deleted successfully"
            })
        except NotFoundError as e:
            return jsonify({"status": "error", "message": str(e)}), e.status_code
        except Exception as e:
            current_app.logger.error(f"Error in delete_data_source: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/data-sources/<int:source_id>/pull', methods=['POST'])
def pull_data_source(source_id):
    """
    Trigger a data pull for a specific data source SYNCHRONOUSLY.
    NOTE: This runs the scraper within the request thread.
    """
    with db_session() as session:
        data_source = session.query(DataSource).get(source_id)
        if not data_source:
            raise NotFoundError(f"Data source with ID {source_id} not found")

        # Check if scraping is already in progress (Optional - requires tracking state)
        # status = session.query(ScraperStatus).filter_by(source_name=data_source.name).first()
        # if status and status.status == 'running':
        #     return jsonify({"message": f"Scraping already in progress for {data_source.name}"}), 409 # Conflict

        # Update status to running
        try:
            status = session.query(ScraperStatus).filter_by(source_name=data_source.name).first()
            if not status:
                status = ScraperStatus(source_name=data_source.name, source_id=source_id)
                session.add(status)
            status.status = "running"
            status.error_message = None
            status.timestamp = datetime.datetime.now() # Use UTCNow? Review model definition
            session.commit()
        except SQLAlchemyError as db_error:
            logger.error(f"Failed to update status to running before pull: {db_error}")
            session.rollback()
            # Decide if we should proceed or return error
            return jsonify({"error": "Database error before starting scrape", "message": str(db_error)}), 500

        scraper_instance = None
        scraper_result = None
        try:
            logger.info(f"Starting synchronous data pull for source: {data_source.name} (ID: {source_id})")

            # --- Select and run the appropriate scraper --- 
            if "Acquisition Gateway" in data_source.name: # Or use a more robust mapping
                scraper_instance = AcquisitionGatewayScraper(session) # Assuming session is needed
            elif "SSA Forecast" in data_source.name:
                scraper_instance = SsaScraper(session) # Assuming session is needed
            else:
                logger.warning(f"No specific scraper found for source: {data_source.name}. Cannot run pull.")
                raise ValueError(f"No scraper configured for data source '{data_source.name}'")

            # Assuming scraper classes have a 'run' method
            scraper_result = scraper_instance.run() 
            # scraper_result could contain summary like {'success': True, 'proposals_added': 5} or raise Exception

            # --- Update status on success --- 
            logger.info(f"Data pull successful for source: {data_source.name}. Result: {scraper_result}")
            status.status = "success"
            status.error_message = None
            status.timestamp = datetime.datetime.now()
            data_source.last_scraped = datetime.datetime.now()
            session.add(data_source) # Add updated data_source to session
            session.commit()

            return jsonify({
                "message": f"Data pull successful for {data_source.name}.",
                "result": scraper_result # Optional: return summary from scraper
                }), 200

        except Exception as e:
            logger.error(f"Error during data pull for source {source_id} ({data_source.name}): {str(e)}")
            logger.error(traceback.format_exc())
            # --- Update status on error --- 
            try:
                # Status object should already be in session from the 'running' update
                status.status = "error"
                status.error_message = str(e)[:1024] # Limit error message length if necessary
                status.timestamp = datetime.datetime.now()
                session.commit()
            except SQLAlchemyError as db_error:
                logger.error(f"Failed to update status after pull error: {db_error}")
                session.rollback()

            return jsonify({"error": "Failed during data pull", "message": str(e)}), 500


@api.route('/data-sources/<int:source_id>/status', methods=['GET'])
def check_scraper_status(source_id):
    """
    Check the status of a data source's scraper.
    
    This endpoint checks the health of a specific data source scraper.
    It returns detailed status information about the scraper, including:
    - Last check time
    - Last successful check time
    - Status (OK, WARNING, ERROR)
    - Error count
    - Error message (if any)
    """
    with db_session() as session:
        try:
            # Find the data source
            source = session.query(DataSource).filter_by(id=source_id).first()
            if not source:
                raise NotFoundError(f"Data source with ID {source_id} not found")
            
            # Get the status record
            status = session.query(ScraperStatus).filter_by(source_id=source_id).first()
            
            # If no status record exists, create a pending check
            if not status:
                return jsonify({
                    "status": "warning",
                    "message": f"No status information available for data source '{source.name}'. Trigger a health check first.",
                    "data": {
                        "source_id": source_id,
                        "source_name": source.name,
                        "status": "UNKNOWN",
                        "last_check": None,
                        "last_success": None,
                        "error_count": 0,
                        "message": "No health checks performed yet"
                    }
                })
            
            # Return the status with subtask_id if available
            response_data = {
                "status": status.status,
                "message": status.error_message,
                "data": {
                    "source_id": source_id,
                    "source_name": source.name,
                    "status": status.status,
                    "message": status.error_message,
                    "last_check": status.last_checked.isoformat() if status.last_checked else None,
                    "last_success": None,  # We'll add this field later if needed
                    "error_count": 0  # We'll track this in the future
                }
            }
            
            # Include subtask_id if it exists
            if hasattr(status, 'subtask_id') and status.subtask_id:
                response_data["data"]["subtask_id"] = status.subtask_id
            
            return jsonify(response_data)
            
        except NotFoundError as e:
            return jsonify({"status": "error", "message": str(e)}), 404
        except Exception as e:
            current_app.logger.error(f"Error in check_scraper_status: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500 