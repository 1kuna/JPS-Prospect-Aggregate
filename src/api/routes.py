"""Routes for the API module."""

from flask import jsonify, request, current_app
from sqlalchemy import func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from src.api import api
from src.database.models import Proposal, DataSource, ScraperStatus
from src.exceptions import ValidationError, NotFoundError
from src.celery_app import celery_app
from src.utils.logger import logger
from src.utils.db_context import db_session, with_db_session
import math
import datetime
import os
import platform
import psutil
import time
import traceback
from celery.result import AsyncResult
import datetime

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


@api.route('/data_sources', methods=['GET'])
def get_data_sources():
    """Get all data sources with their status."""
    with db_session() as session:
        data_sources = session.query(DataSource).all()
        
        # Get the latest status for each data source
        statuses = session.query(ScraperStatus).all()
        status_dict = {status.source_name: status for status in statuses}
        
        result = []
        for source in data_sources:
            source_dict = source.to_dict()
            status = status_dict.get(source.name)
            if status:
                source_dict['status'] = status.status
                source_dict['last_error'] = status.error_message
                source_dict['last_check'] = status.timestamp.isoformat() if status.timestamp else None
            result.append(source_dict)
        
        return jsonify(result)


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
            
            # Get upcoming proposals
            today = datetime.datetime.now().date()
            upcoming_proposals = session.query(Proposal).filter(
                Proposal.proposal_date >= today
            ).order_by(Proposal.proposal_date).limit(5).all()
            
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
                            "proposal_date": p.proposal_date.isoformat() if p.proposal_date else None
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
    Manually trigger a data source pull.
    
    This endpoint starts a Celery task to pull data from the specified source.
    It returns the task ID which can be used to check the status of the task.
    """
    with db_session() as session:
        try:
            # Find the data source
            source = session.query(DataSource).filter_by(id=source_id).first()
            if not source:
                raise NotFoundError(f"Data source with ID {source_id} not found")
            
            # Get task parameters
            params = request.json or {}
            debug = params.get('debug', False)
            force = params.get('force', False)
            
            # Calculate the cooldown period
            cooldown_hours = params.get('cooldown_hours', 6)
            cooldown_time = datetime.datetime.now() - datetime.timedelta(hours=cooldown_hours)
            
            # Check if the source was recently scraped
            if source.last_scraped and source.last_scraped > cooldown_time and not force:
                return jsonify({
                    "status": "warning",
                    "message": f"Data source was recently scraped at {source.last_scraped.isoformat()}. Use force=true to override the cooldown period."
                }), 200
            
            # Start the scraper task using the new simplified task system
            from src.tasks.scrapers import run_all_scrapers, run_acquisition_gateway, run_ssa_contract_forecast
            
            # Choose the appropriate task based on the source name
            if "Acquisition Gateway" in source.name:
                task_result = run_acquisition_gateway.delay(force=True)
            elif "SSA Contract Forecast" in source.name:
                task_result = run_ssa_contract_forecast.delay(force=True)
            else:
                # Use a general task
                task_result = run_all_scrapers.delay(force=True)
            
            task = task_result
            
            # Update the source's last_scraped timestamp
            source.last_scraped = datetime.datetime.now()
            
            # Create or update the ScraperStatus record
            status_record = session.query(ScraperStatus).filter_by(source_id=source_id).first()
            if status_record:
                # Update existing record
                status_record.status = "running"
                status_record.last_checked = datetime.datetime.now()
                status_record.error_message = None
                status_record.subtask_id = task.id
            else:
                # Create new record
                new_status = ScraperStatus(
                    source_id=source_id,
                    status="running",
                    last_checked=datetime.datetime.now(),
                    error_message=None,
                    subtask_id=task.id
                )
                session.add(new_status)
            
            session.commit()
            
            return jsonify({
                "status": "success",
                "message": f"Data pull task started for source {source.name}",
                "data": {
                    "task_id": task.id,
                    "source_id": source_id,
                    "source_name": source.name
                }
            })
        except NotFoundError as e:
            return jsonify({"status": "error", "message": str(e)}), e.status_code
        except Exception as e:
            current_app.logger.error(f"Error in pull_data_source: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    Get the status of a Celery task.
    
    Args:
        task_id: The ID of the task to check
        
    Returns:
        Task status information
    """
    try:
        task = AsyncResult(task_id, app=celery_app)
        
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'status': 'Task is pending...'
            }
        elif task.state == 'FAILURE':
            response = {
                'state': task.state,
                'status': 'Task failed',
                'error': str(task.info)
            }
        else:
            response = {
                'state': task.state,
                'status': task.info.get('status', '') if isinstance(task.info, dict) else str(task.info)
            }
            
            # If the task is successful and has a result, include it
            if task.state == 'SUCCESS' and isinstance(task.info, dict):
                response.update(task.info)
        
        return jsonify(response)
    except Exception as e:
        current_app.logger.error(f"Error checking task status: {str(e)}")
        return jsonify({
            'state': 'ERROR',
            'status': 'Error checking task status',
            'error': str(e)
        }), 500


@api.route('/statistics', methods=['GET'])
def get_statistics():
    """
    Get statistics and aggregated data from the database.
    
    This endpoint returns various statistics and aggregated data about the
    proposals in the database, such as:
    - Total number of proposals
    - Proposals by agency
    - Proposals by date
    - Proposals by value range
    - etc.
    """
    with db_session() as session:
        try:
            result = {
                "total_proposals": 0,
                "by_agency": [],
                "by_value_range": [],
                "by_month": [],
                "by_source": [],
                "latest_proposals": []
            }
            
            # Total number of proposals
            result["total_proposals"] = session.query(func.count(Proposal.id)).scalar()
            
            # Proposals by agency (top 10)
            agency_counts = session.query(
                Proposal.agency,
                func.count(Proposal.id).label('count')
            ).group_by(Proposal.agency).order_by(desc('count')).limit(10).all()
            
            result["by_agency"] = [
                {"agency": agency, "count": count}
                for agency, count in agency_counts
            ]
            
            # Proposals by value range
            value_ranges = [
                (0, 100000, "0-100K"),
                (100000, 500000, "100K-500K"),
                (500000, 1000000, "500K-1M"),
                (1000000, 5000000, "1M-5M"),
                (5000000, 10000000, "5M-10M"),
                (10000000, float('inf'), "10M+")
            ]
            
            for min_val, max_val, label in value_ranges:
                if max_val == float('inf'):
                    count = session.query(func.count(Proposal.id)).filter(
                        Proposal.estimated_value >= min_val
                    ).scalar()
                else:
                    count = session.query(func.count(Proposal.id)).filter(
                        Proposal.estimated_value >= min_val,
                        Proposal.estimated_value < max_val
                    ).scalar()
                
                result["by_value_range"].append({
                    "range": label,
                    "count": count
                })
            
            # Proposals by month (last 12 months)
            current_date = datetime.datetime.now().date()
            start_date = current_date.replace(day=1) - datetime.timedelta(days=365)
            
            # Generate a list of all months in the range
            months = []
            current_month = start_date.replace(day=1)
            while current_month <= current_date:
                months.append(current_month)
                # Move to next month
                if current_month.month == 12:
                    current_month = current_month.replace(year=current_month.year + 1, month=1)
                else:
                    current_month = current_month.replace(month=current_month.month + 1)
            
            # Query proposals by month
            for month_start in months:
                # Calculate end of month
                if month_start.month == 12:
                    month_end = month_start.replace(year=month_start.year + 1, month=1) - datetime.timedelta(days=1)
                else:
                    month_end = month_start.replace(month=month_start.month + 1) - datetime.timedelta(days=1)
                
                # Count proposals with proposal dates in this month
                count = session.query(func.count(Proposal.id)).filter(
                    Proposal.proposal_date >= month_start,
                    Proposal.proposal_date <= month_end
                ).scalar()
                
                result["by_month"].append({
                    "month": month_start.strftime("%Y-%m"),
                    "count": count
                })
            
            # Proposals by source
            source_counts = session.query(
                DataSource.id,
                DataSource.name,
                func.count(Proposal.id).label('count')
            ).join(Proposal, Proposal.source_id == DataSource.id).group_by(
                DataSource.id,
                DataSource.name
            ).all()
            
            result["by_source"] = [
                {"id": source_id, "name": name, "count": count}
                for source_id, name, count in source_counts
            ]
            
            # Latest proposals
            latest_proposals = session.query(Proposal).order_by(
                desc(Proposal.created_at)
            ).limit(10).all()
            
            result["latest_proposals"] = [
                {
                    "id": p.id,
                    "title": p.title,
                    "agency": p.agency,
                    "estimated_value": p.estimated_value,
                    "proposal_date": p.proposal_date.isoformat() if p.proposal_date else None,
                    "created_at": p.created_at.isoformat()
                }
                for p in latest_proposals
            ]
            
            return jsonify({
                "status": "success",
                "data": result
            })
        except Exception as e:
            current_app.logger.error(f"Error in get_statistics: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({"status": "error", "message": str(e)}), 500


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


@api.route('/data-sources/<int:source_id>/health-check', methods=['POST'])
def trigger_health_check(source_id):
    """
    Trigger a health check for a specific data source.
    
    This endpoint starts a Celery task to check the health of a data source.
    It returns the task ID which can be used to check the status of the task.
    """
    with db_session() as session:
        try:
            # Find the data source
            source = session.query(DataSource).filter_by(id=source_id).first()
            if not source:
                raise NotFoundError(f"Data source with ID {source_id} not found")
            
            # Determine which health check task to use based on the source name
            from src.tasks.health import check_acquisition_gateway, check_ssa_contract_forecast, check_all_scrapers
            
            if "Acquisition Gateway" in source.name:
                task_result = check_acquisition_gateway.delay()
            elif "SSA Contract Forecast" in source.name:
                task_result = check_ssa_contract_forecast.delay()
            else:
                # Default to all scrapers task if source name doesn't match
                task_result = check_all_scrapers.delay()
            
            task = task_result
            
            return jsonify({
                "status": "success",
                "message": f"Health check task started for source {source.name}",
                "data": {
                    "task_id": task.id,
                    "source_id": source_id,
                    "source_name": source.name
                }
            })
        except NotFoundError as e:
            return jsonify({"status": "error", "message": str(e)}), e.status_code
        except Exception as e:
            current_app.logger.error(f"Error in trigger_health_check: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500 