"""Routes for the API blueprint."""

from flask import jsonify, request, current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from . import api
from src.database.db import session_scope
from src.database.models import Proposal, DataSource, ScraperStatus
import datetime
from src.exceptions import ValidationError, ResourceNotFoundError, DatabaseError

@api.route('/proposals')
def get_proposals():
    """API endpoint to get proposals with filtering and sorting."""
    try:
        # Validate query parameters
        sort_by = request.args.get("sort_by", "release_date")
        valid_sort_fields = ["release_date", "title", "agency", "value", "status", "naics_code", "created_at", "updated_at"]
        if sort_by not in valid_sort_fields:
            raise ValidationError(f"Invalid sort_by parameter: {sort_by}. Valid options are: {', '.join(valid_sort_fields)}")
        
        sort_order = request.args.get("sort_order", "desc").lower()
        if sort_order not in ["asc", "desc"]:
            raise ValidationError(f"Invalid sort_order parameter: {sort_order}. Valid options are: asc, desc")
        
        # Validate pagination parameters
        try:
            page = int(request.args.get("page", 1))
            if page < 1:
                raise ValidationError("Page number must be greater than or equal to 1")
        except ValueError:
            raise ValidationError("Page number must be an integer")
            
        try:
            per_page = int(request.args.get("per_page", 20))
            if per_page < 1 or per_page > 100:
                raise ValidationError("Items per page must be between 1 and 100")
        except ValueError:
            raise ValidationError("Items per page must be an integer")
        
        # Process other parameters
        agency = request.args.get("agency")
        source_id = request.args.get("source_id")
        status = request.args.get("status")
        search = request.args.get("search")
        naics_codes = request.args.getlist("naics_codes[]")
        only_latest = request.args.get("only_latest", "true").lower() == "true"
        
        with session_scope() as session:
            # Start building the query
            query = session.query(Proposal)
            
            # Apply filters
            if agency:
                query = query.filter(Proposal.agency == agency)
            
            if source_id:
                try:
                    source_id = int(source_id)
                    query = query.filter(Proposal.source_id == source_id)
                except ValueError:
                    raise ValidationError("source_id must be an integer")
            
            if status:
                query = query.filter(Proposal.status == status)
            
            # Apply NAICS codes filter if provided
            if naics_codes:
                query = query.filter(Proposal.naics_code.in_(naics_codes))
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (Proposal.title.ilike(search_term)) |
                    (Proposal.description.ilike(search_term)) |
                    (Proposal.agency.ilike(search_term)) |
                    (Proposal.office.ilike(search_term))
                )
            
            # Check if the is_latest column exists and filter if needed
            if only_latest:
                try:
                    # Try to filter by is_latest
                    query = query.filter(Proposal.is_latest == True)
                except Exception as e:
                    # Column doesn't exist yet, skip this filter
                    current_app.logger.warning(f"Could not filter by is_latest: {e}")
            
            # Apply sorting
            if sort_order == "asc":
                query = query.order_by(getattr(Proposal, sort_by).asc())
            else:
                query = query.order_by(getattr(Proposal, sort_by).desc())
            
            # Apply pagination
            total_count = query.count()
            query = query.limit(per_page).offset((page - 1) * per_page)
            
            # Execute query and format results
            proposals = query.all()
            
            if not proposals and page > 1:
                raise ResourceNotFoundError(f"No proposals found for page {page}")
            
            result = {
                "status": "success",
                "data": [p.to_dict() for p in proposals],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": (total_count + per_page - 1) // per_page
                }
            }
            
            return jsonify(result)
            
    except ValidationError as e:
        current_app.logger.warning(f"Validation error in get_proposals: {e.message}")
        return jsonify(e.to_dict()), e.status_code
        
    except ResourceNotFoundError as e:
        current_app.logger.info(f"Resource not found in get_proposals: {e.message}")
        return jsonify(e.to_dict()), e.status_code
        
    except DatabaseError as e:
        current_app.logger.error(f"Database error in get_proposals: {e.message}")
        return jsonify(e.to_dict()), e.status_code
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_proposals: {str(e)}")
        error_response = {
            "status": "error",
            "message": "An unexpected error occurred",
            "error_code": "INTERNAL_ERROR"
        }
        return jsonify(error_response), 500

@api.route('/sources')
def get_sources():
    """API endpoint to get all data sources."""
    session = get_session()
    try:
        sources = session.query(DataSource).all()
        return jsonify({
            "sources": [
                {
                    "id": source.id,
                    "name": source.name,
                    "url": source.url,
                    "description": source.description,
                    "last_scraped": source.last_scraped.isoformat() if source.last_scraped else None
                }
                for source in sources
            ]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting sources: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        close_session(session)

@api.route('/filters')
def get_filters():
    """API endpoint to get filter options."""
    session = get_session()
    
    try:
        # Get unique agencies
        agencies = [r[0] for r in session.query(Proposal.agency).distinct().all() if r[0]]
        
        # Get unique statuses
        statuses = [r[0] for r in session.query(Proposal.status).distinct().all() if r[0]]
        
        # Get unique NAICS codes
        naics_codes = [r[0] for r in session.query(Proposal.naics_code).distinct().all() if r[0]]
        
        return jsonify({
            "agencies": agencies,
            "statuses": statuses,
            "naics_codes": naics_codes
        })
    
    finally:
        close_session(session)

@api.route('/scraper-status')
def get_scraper_status():
    """API endpoint to get the status of all scrapers."""
    session = get_session()
    
    try:
        # Join ScraperStatus with DataSource to get the status of all scrapers
        results = session.query(
            ScraperStatus, DataSource
        ).join(
            DataSource, ScraperStatus.source_id == DataSource.id
        ).all()
        
        # Format the results
        status_data = []
        for status, source in results:
            status_data.append({
                "source_id": source.id,
                "source_name": source.name,
                "last_run": status.last_run.isoformat() if status.last_run else None,
                "status": status.status,
                "message": status.message,
                "next_run": status.next_run.isoformat() if status.next_run else None
            })
        
        return jsonify(status_data)
    
    except Exception as e:
        current_app.logger.error(f"Error getting scraper status: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        close_session(session)

@api.route('/scraper-status/check', methods=['POST'])
def check_scraper_health():
    """API endpoint to run health checks for all scrapers."""
    try:
        # This would typically trigger a background task to check scraper health
        # For now, we'll just return a success message
        return jsonify({"success": True, "message": "Health checks started"})
    
    except Exception as e:
        current_app.logger.error(f"Error starting health checks: {e}")
        return jsonify({"error": str(e)}), 500

@api.route('/scraper-status/<int:source_id>', methods=['GET'])
def get_scraper_health(source_id):
    """API endpoint to get the health status of a specific scraper."""
    session = get_session()
    
    try:
        # Get the scraper status for the specified source
        status = session.query(ScraperStatus).filter(ScraperStatus.source_id == source_id).first()
        
        if not status:
            return jsonify({"error": f"No status found for source ID {source_id}"}), 404
        
        # Return the status
        return jsonify({
            "source_id": source_id,
            "last_run": status.last_run.isoformat() if status.last_run else None,
            "status": status.status,
            "message": status.message,
            "next_run": status.next_run.isoformat() if status.next_run else None
        })
    
    except Exception as e:
        current_app.logger.error(f"Error getting scraper health: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        close_session(session)

@api.route('/statistics')
def get_statistics():
    """API endpoint to get statistics about the proposals."""
    session = get_session()
    
    try:
        # Check if we should only count the latest proposals
        only_latest = request.args.get("only_latest", "false").lower() == "true"
        
        # Start with a base query
        base_query = session.query(Proposal)
        
        # Apply latest filter if requested
        if only_latest:
            try:
                base_query = base_query.filter(Proposal.is_latest == True)
            except Exception as e:
                current_app.logger.warning(f"Could not filter by is_latest: {e}")
        
        # Get total number of proposals
        total_proposals = base_query.count()
        
        # Get proposals by agency
        agency_query = session.query(
            Proposal.agency, 
            func.count(Proposal.id)
        )
        if only_latest:
            try:
                agency_query = agency_query.filter(Proposal.is_latest == True)
            except Exception:
                pass
        agency_counts = agency_query.group_by(Proposal.agency).all()
        
        # Get proposals by status
        status_query = session.query(
            Proposal.status, 
            func.count(Proposal.id)
        )
        if only_latest:
            try:
                status_query = status_query.filter(Proposal.is_latest == True)
            except Exception:
                pass
        status_counts = status_query.group_by(Proposal.status).all()
        
        # Get proposals by month
        month_counts = []
        if hasattr(Proposal, 'release_date'):
            month_query = session.query(
                func.strftime('%Y-%m', Proposal.release_date).label('month'),
                func.count(Proposal.id)
            ).filter(Proposal.release_date != None)
            
            if only_latest:
                try:
                    month_query = month_query.filter(Proposal.is_latest == True)
                except Exception:
                    pass
            
            month_counts = month_query.group_by('month').all()
        
        # Get proposals by source
        source_query = session.query(
            DataSource.name,
            func.count(Proposal.id)
        ).join(
            DataSource, Proposal.source_id == DataSource.id
        )
        
        if only_latest:
            try:
                source_query = source_query.filter(Proposal.is_latest == True)
            except Exception:
                pass
        
        source_counts = source_query.group_by(DataSource.name).all()
        
        # Format the data as dictionaries
        by_agency = {agency: count for agency, count in agency_counts if agency}
        by_status = {status: count for status, count in status_counts if status}
        by_month = {month: count for month, count in month_counts if month}
        by_source = {name: count for name, count in source_counts}
        
        # Return the statistics
        return jsonify({
            "total_proposals": total_proposals,
            "by_agency": by_agency,
            "by_status": by_status,
            "by_month": by_month,
            "by_source": by_source,
            "only_latest": only_latest
        })
    
    except Exception as e:
        current_app.logger.error(f"Error getting statistics: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        close_session(session) 