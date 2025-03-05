"""Routes for the API blueprint."""

from flask import jsonify, request, current_app
from sqlalchemy import func
from . import api
from src.database.db import get_session, close_session
from src.database.models import Proposal, DataSource, ScraperStatus
import datetime

@api.route('/proposals')
def get_proposals():
    """API endpoint to get proposals with filtering and sorting."""
    session = get_session()
    
    try:
        # Get query parameters
        agency = request.args.get("agency")
        source_id = request.args.get("source_id")
        status = request.args.get("status")
        search = request.args.get("search")
        sort_by = request.args.get("sort_by", "release_date")
        sort_order = request.args.get("sort_order", "desc")
        
        # Get NAICS codes filter (can be multiple)
        naics_codes = request.args.getlist("naics_codes[]")
        
        # Check if we should only get the latest proposals
        only_latest = request.args.get("only_latest", "true").lower() == "true"
        
        # Start building the query
        query = session.query(Proposal)
        
        # Apply filters
        if agency:
            query = query.filter(Proposal.agency == agency)
        
        if source_id:
            query = query.filter(Proposal.source_id == source_id)
        
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
            except Exception:
                # Column doesn't exist yet, skip this filter
                pass
        
        # Apply sorting
        if sort_order.lower() == "asc":
            query = query.order_by(getattr(Proposal, sort_by).asc())
        else:
            query = query.order_by(getattr(Proposal, sort_by).desc())
        
        # Execute the query
        proposals = query.all()
        
        # Convert to JSON
        result = []
        for proposal in proposals:
            result.append({
                "id": proposal.id,
                "source_id": proposal.source_id,
                "external_id": proposal.external_id,
                "title": proposal.title,
                "agency": proposal.agency,
                "office": proposal.office,
                "description": proposal.description,
                "naics_code": proposal.naics_code,
                "estimated_value": proposal.estimated_value,
                "release_date": proposal.release_date.isoformat() if proposal.release_date else None,
                "response_date": proposal.response_date.isoformat() if proposal.response_date else None,
                "contact_info": proposal.contact_info,
                "url": proposal.url,
                "status": proposal.status,
                "last_updated": proposal.last_updated.isoformat() if proposal.last_updated else None,
                "imported_at": proposal.imported_at.isoformat() if proposal.imported_at else None,
                
                # Include the new fields
                "contract_type": proposal.contract_type,
                "set_aside": proposal.set_aside,
                "competition_type": proposal.competition_type,
                "solicitation_number": proposal.solicitation_number,
                "award_date": proposal.award_date.isoformat() if proposal.award_date else None,
                "place_of_performance": proposal.place_of_performance,
                "incumbent": proposal.incumbent
            })
        
        return jsonify(result)
    
    finally:
        close_session(session)

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
        
        # Convert to JSON
        status_data = []
        for status, source in results:
            status_data.append({
                "id": status.id,
                "source_id": status.source_id,
                "source_name": source.name,
                "status": status.status,
                "last_checked": status.last_checked.isoformat() if status.last_checked else None,
                "error_message": status.error_message,
                "response_time": status.response_time
            })
        
        return jsonify({
            "scraper_status": status_data
        })
    
    except Exception as e:
        current_app.logger.error(f"Error getting scraper status: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        close_session(session)

@api.route('/statistics')
def get_statistics():
    """API endpoint to get statistics about the proposals."""
    session = get_session()
    
    try:
        # Get total number of proposals
        total_proposals = session.query(Proposal).count()
        
        # Get proposals by agency
        agency_counts = session.query(
            Proposal.agency, 
            func.count(Proposal.id)
        ).group_by(Proposal.agency).all()
        
        # Get proposals by status
        status_counts = session.query(
            Proposal.status, 
            func.count(Proposal.id)
        ).group_by(Proposal.status).all()
        
        # Get proposals by month
        month_counts = []
        if hasattr(Proposal, 'release_date'):
            # This query gets the count of proposals by month
            month_counts = session.query(
                func.strftime('%Y-%m', Proposal.release_date).label('month'),
                func.count(Proposal.id)
            ).filter(Proposal.release_date != None).group_by('month').all()
        
        # Get proposals by source
        source_counts = session.query(
            DataSource.name,
            func.count(Proposal.id)
        ).join(
            DataSource, Proposal.source_id == DataSource.id
        ).group_by(DataSource.name).all()
        
        # Return the statistics
        return jsonify({
            "total_proposals": total_proposals,
            "by_agency": {agency: count for agency, count in agency_counts if agency},
            "by_status": {status: count for status, count in status_counts if status},
            "by_month": {month: count for month, count in month_counts if month},
            "by_source": {name: count for name, count in source_counts}
        })
    
    except Exception as e:
        current_app.logger.error(f"Error getting statistics: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        close_session(session) 