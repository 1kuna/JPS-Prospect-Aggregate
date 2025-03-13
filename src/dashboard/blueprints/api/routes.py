"""Routes for the API blueprint."""

from flask import jsonify, request, current_app
from sqlalchemy import func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from . import api
from src.database.db_session_manager import session_scope, check_connection, get_connection_stats
from src.database.models import Proposal, DataSource, ScraperStatus
from src.exceptions import ValidationError, ResourceNotFoundError
from src.celery_app import celery_app
import math
import datetime
import logging
import os
import platform
import psutil
import time

# Set up logging
logger = logging.getLogger(__name__)

def paginate_query(query, page, per_page):
    """Helper function to paginate query results."""
    # Validate pagination parameters
    try:
        page = int(page)
        if page < 1:
            raise ValidationError("Page number must be greater than or equal to 1")
    except (ValueError, TypeError):
        raise ValidationError("Page number must be an integer")
        
    try:
        per_page = int(per_page)
        if per_page < 1 or per_page > 500:
            raise ValidationError("Items per page must be between 1 and 500")
    except (ValueError, TypeError):
        raise ValidationError("Items per page must be an integer")
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply pagination
    paginated_query = query.limit(per_page).offset((page - 1) * per_page)
    
    # Calculate total pages
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
    
    return {
        "query": paginated_query,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages
        }
    }

@api.route('/proposals')
def get_proposals():
    """API endpoint to get proposals with sorting and pagination."""
    # Validate sort parameters
    sort_by = request.args.get("sort_by", "release_date")
    valid_sort_fields = ["release_date", "title", "agency", "value", "status", "naics_code", "created_at", "updated_at"]
    if sort_by not in valid_sort_fields:
        raise ValidationError(f"Invalid sort_by parameter: {sort_by}. Valid options are: {', '.join(valid_sort_fields)}")
    
    sort_order = request.args.get("sort_order", "desc").lower()
    if sort_order not in ["asc", "desc"]:
        raise ValidationError(f"Invalid sort_order parameter: {sort_order}. Valid options are: asc, desc")
    
    with session_scope() as session:
        # Start building the query
        query = session.query(Proposal)
        
        # Apply sorting
        if sort_order == "asc":
            query = query.order_by(getattr(Proposal, sort_by).asc())
        else:
            query = query.order_by(getattr(Proposal, sort_by).desc())
        
        # Apply pagination
        page = request.args.get("page", 1)
        per_page = request.args.get("per_page", 50)
        pagination_result = paginate_query(query, page, per_page)
        
        # Execute query and get results
        proposals = pagination_result["query"].all()
        
        if not proposals and int(page) > 1:
            raise ResourceNotFoundError(f"No proposals found for page {page}")
        
        # Format the response
        result = {
            "status": "success",
            "data": [proposal.to_dict() for proposal in proposals],
            "pagination": pagination_result["pagination"]
        }
        
        return jsonify(result)

@api.route('/dashboard')
def get_dashboard():
    """API endpoint to get dashboard data."""
    with session_scope() as session:
        # Get proposal counts
        total_proposals = session.query(func.count(Proposal.id)).scalar() or 0
        
        # Get data source counts
        total_sources = session.query(func.count(DataSource.id)).scalar() or 0
        
        # Get recent proposals
        recent_proposals = session.query(Proposal).order_by(Proposal.release_date.desc()).limit(5).all()
        
        # Format the response
        result = {
            "status": "success",
            "data": {
                "counts": {
                    "total_proposals": total_proposals,
                    "total_sources": total_sources
                },
                "recent_proposals": [proposal.to_dict() for proposal in recent_proposals]
            }
        }
        
        return jsonify(result)

@api.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to monitor the application's health.
    
    Returns:
        JSON response with health status information.
    """
    start_time = time.time()
    
    # Check database connection
    db_status = "healthy" if check_connection() else "unhealthy"
    
    # Check Redis connection (for Celery)
    redis_status = "unknown"
    try:
        # Ping Redis through Celery
        redis_ping = celery_app.backend.client.ping()
        redis_status = "healthy" if redis_ping else "unhealthy"
    except Exception as e:
        logger.warning(f"Redis health check failed: {str(e)}")
        redis_status = "unhealthy"
    
    # Get system information
    system_info = {
        "os": platform.system(),
        "python_version": platform.python_version(),
        "cpu_usage": psutil.cpu_percent(interval=0.1),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent
    }
    
    # Get database connection stats
    try:
        db_stats = get_connection_stats()
    except Exception as e:
        logger.warning(f"Failed to get database connection stats: {str(e)}")
        db_stats = {"error": str(e)}
    
    # Get Celery worker status
    celery_status = "unknown"
    worker_stats = {}
    try:
        # Get active workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            celery_status = "healthy"
            worker_stats = {
                "active_workers": len(active_workers),
                "worker_names": list(active_workers.keys()),
                "active_tasks": sum(len(tasks) for tasks in active_workers.values())
            }
        else:
            celery_status = "unhealthy"
            worker_stats = {"error": "No active workers found"}
    except Exception as e:
        logger.warning(f"Celery health check failed: {str(e)}")
        celery_status = "unhealthy"
        worker_stats = {"error": str(e)}
    
    # Get data source information
    data_sources = []
    try:
        with session_scope() as session:
            sources = session.query(DataSource).all()
            for source in sources:
                # Get the latest status check for this source
                latest_status = session.query(ScraperStatus).filter(
                    ScraperStatus.source_id == source.id
                ).order_by(ScraperStatus.last_checked.desc()).first()
                
                data_sources.append({
                    "id": source.id,
                    "name": source.name,
                    "last_scraped": source.last_scraped.isoformat() if source.last_scraped else None,
                    "status": latest_status.status if latest_status else "unknown",
                    "last_checked": latest_status.last_checked.isoformat() if latest_status and latest_status.last_checked else None
                })
    except Exception as e:
        logger.warning(f"Failed to get data source information: {str(e)}")
        data_sources = [{"error": str(e)}]
    
    # Calculate response time
    response_time = time.time() - start_time
    
    # Determine overall health status
    overall_status = "healthy"
    if db_status != "healthy" or redis_status != "healthy" or celery_status != "healthy":
        overall_status = "degraded"
        if db_status == "unhealthy" and redis_status == "unhealthy":
            overall_status = "unhealthy"
    
    return jsonify({
        "status": overall_status,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "response_time": response_time,
        "components": {
            "database": {
                "status": db_status,
                "stats": db_stats
            },
            "redis": {
                "status": redis_status
            },
            "celery": {
                "status": celery_status,
                "stats": worker_stats
            }
        },
        "system": system_info,
        "data_sources": data_sources,
        "version": os.getenv("APP_VERSION", "1.0.0")
    })

@api.route('/data-sources', methods=['GET'])
def get_data_sources():
    """Get all data sources."""
    with session_scope() as session:
        sources = session.query(DataSource).all()
        
        # Format the response
        result = {
            "status": "success",
            "data": [source.to_dict() for source in sources]
        }
        
        return jsonify(result)

@api.route('/data-sources/<int:source_id>', methods=['PUT'])
def update_data_source(source_id):
    """API endpoint to update a data source."""
    data = request.get_json()
    if not data:
        raise ValidationError("No data provided")
    
    with session_scope() as session:
        source = session.query(DataSource).filter(DataSource.id == source_id).first()
        if not source:
            raise ResourceNotFoundError(f"Data source with ID {source_id} not found")
        
        # Update source attributes
        for key, value in data.items():
            if hasattr(source, key):
                setattr(source, key, value)
        
        session.commit()
        
        # Format the response
        result = {
            "status": "success",
            "data": source.to_dict(),
            "message": f"Data source with ID {source_id} updated successfully"
        }
        
        return jsonify(result)

@api.route('/data-sources', methods=['POST'])
def create_data_source():
    """API endpoint to create a new data source."""
    data = request.get_json()
    if not data:
        raise ValidationError("No data provided")
    
    with session_scope() as session:
        # Create new data source
        source = DataSource(**data)
        session.add(source)
        session.commit()
        
        # Format the response
        result = {
            "status": "success",
            "data": source.to_dict(),
            "message": "Data source created successfully"
        }
        
        return jsonify(result), 201

@api.route('/data-sources/<int:source_id>', methods=['DELETE'])
def delete_data_source(source_id):
    """API endpoint to delete a data source."""
    with session_scope() as session:
        source = session.query(DataSource).filter(DataSource.id == source_id).first()
        if not source:
            raise ResourceNotFoundError(f"Data source with ID {source_id} not found")
        
        session.delete(source)
        session.commit()
        
        # Format the response
        result = {
            "status": "success",
            "message": f"Data source with ID {source_id} deleted successfully"
        }
        
        return jsonify(result)

@api.route('/statistics', methods=['GET'])
def get_statistics():
    """API endpoint to get statistics about proposals."""
    try:
        with session_scope() as session:
            # Get total proposals count
            total_proposals = session.query(func.count(Proposal.id)).scalar() or 0
            
            # Get proposals by data source
            source_stats = []
            source_query = session.query(
                DataSource.name,
                func.count(Proposal.id).label('count')
            ).outerjoin(
                Proposal, DataSource.id == Proposal.source_id
            ).group_by(
                DataSource.name
            ).order_by(
                desc('count')
            ).all()
            
            for name, count in source_query:
                source_stats.append({
                    'name': name,
                    'count': count
                })
            
            # Get proposals by agency
            agency_stats = []
            agency_query = session.query(
                Proposal.agency,
                func.count(Proposal.id).label('count')
            ).filter(
                Proposal.agency.isnot(None)
            ).group_by(
                Proposal.agency
            ).order_by(
                desc('count')
            ).limit(10).all()
            
            for agency, count in agency_query:
                agency_stats.append({
                    'name': agency or 'Unknown',
                    'count': count
                })
            
            # Get proposals by status
            status_stats = []
            status_query = session.query(
                Proposal.status,
                func.count(Proposal.id).label('count')
            ).filter(
                Proposal.status.isnot(None)
            ).group_by(
                Proposal.status
            ).order_by(
                desc('count')
            ).all()
            
            for status, count in status_query:
                status_stats.append({
                    'name': status or 'Unknown',
                    'count': count
                })
            
            # Return the statistics
            return jsonify({
                'total_proposals': total_proposals,
                'source_stats': source_stats,
                'agency_stats': agency_stats,
                'status_stats': status_stats
            })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_statistics: {str(e)}")
        return jsonify({
            'error': 'Database error',
            'message': str(e)
        }), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_statistics: {str(e)}")
        return jsonify({
            'error': 'Server error',
            'message': str(e)
        }), 500 