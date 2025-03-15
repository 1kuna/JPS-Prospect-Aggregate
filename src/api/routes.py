"""Routes for the API module."""

from flask import jsonify, request, current_app
from sqlalchemy import func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from src.api import api
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
import traceback
from celery.result import AsyncResult

# Set up logging
logger = logging.getLogger(__name__)

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


@api.route('/proposals')
def get_proposals():
    """Get all proposals with filtering and pagination."""
    try:
        # Get query parameters
        page = request.args.get('page', 1)
        per_page = request.args.get('per_page', 20)
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'asc')
        filter_agency = request.args.get('agency')
        filter_title = request.args.get('title')
        filter_min_value = request.args.get('min_value')
        filter_source_id = request.args.get('source_id')
        
        with session_scope() as session:
            # Query
            query = session.query(Proposal).join(DataSource)
            
            # Apply filters
            if filter_agency:
                query = query.filter(Proposal.agency.ilike(f'%{filter_agency}%'))
            if filter_title:
                query = query.filter(Proposal.title.ilike(f'%{filter_title}%'))
            if filter_min_value:
                query = query.filter(Proposal.estimated_value >= float(filter_min_value))
            if filter_source_id:
                query = query.filter(Proposal.source_id == int(filter_source_id))
            
            # Apply sorting
            if sort_by in ['id', 'title', 'agency', 'estimated_value', 'release_date', 'response_date']:
                sort_column = getattr(Proposal, sort_by)
                query = query.order_by(asc(sort_column) if sort_order.lower() == 'asc' else desc(sort_column))
            else:
                query = query.order_by(Proposal.id)
            
            # Apply pagination
            proposals_query, pagination = paginate_query(query, page, per_page)
            
            # Convert to JSON-serializable format
            proposals = []
            for proposal in proposals_query:
                proposals.append({
                    "id": proposal.id,
                    "title": proposal.title,
                    "agency": proposal.agency,
                    "description": proposal.description,
                    "solicitation_number": proposal.solicitation_number,
                    "release_date": proposal.release_date.isoformat() if proposal.release_date else None,
                    "response_date": proposal.response_date.isoformat() if proposal.response_date else None,
                    "estimated_value": proposal.estimated_value,
                    "source_id": proposal.source_id,
                    "source_name": proposal.source.name
                })
            
            return jsonify({
                "status": "success",
                "data": proposals,
                "pagination": pagination
            })
            
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error in get_proposals: {str(e)}")
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500


@api.route('/dashboard')
def get_dashboard():
    """Get dashboard summary information."""
    with session_scope() as session:
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


@api.route('/health', methods=['GET'])
def health_check():
    """
    Perform a health check of the application.
    
    This endpoint checks:
    1. Database connection
    2. Celery worker status
    3. System resources (CPU, memory)
    4. Data source health checks
    """
    health_data = {
        "status": "OK",
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "timestamp": datetime.datetime.now().isoformat(),
        "components": {}
    }
    
    overall_status = True
    
    # Check database connection
    try:
        db_connected, stats = check_connection()
        health_data["components"]["database"] = {
            "status": "OK" if db_connected else "ERROR",
            "connection_time_ms": stats.get("connection_time_ms"),
            "query_time_ms": stats.get("query_time_ms"),
            "message": "Connected" if db_connected else "Connection failed"
        }
        overall_status = overall_status and db_connected
    except Exception as e:
        health_data["components"]["database"] = {
            "status": "ERROR",
            "message": str(e)
        }
        overall_status = False
    
    # Check Celery status
    try:
        i = celery_app.control.inspect()
        ping = i.ping()
        stats = i.stats()
        active_tasks = i.active()
        
        # Check if any workers responded
        workers_responding = ping is not None and len(ping) > 0
        
        health_data["components"]["celery"] = {
            "status": "OK" if workers_responding else "WARNING",
            "workers": len(ping) if ping else 0,
            "active_tasks": sum(len(tasks) for worker, tasks in active_tasks.items()) if active_tasks else 0,
            "message": "Workers responding" if workers_responding else "No workers responding"
        }
        
        # If no workers are responding, consider it a warning but not a critical failure
        if not workers_responding:
            health_data["components"]["celery"]["status"] = "WARNING"
    except Exception as e:
        health_data["components"]["celery"] = {
            "status": "ERROR",
            "message": str(e)
        }
        # Don't fail the overall health check due to Celery issues
        health_data["components"]["celery"]["status"] = "WARNING"
    
    # Check system resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_data["components"]["system"] = {
            "status": "OK",
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count()
            },
            "memory": {
                "total_mb": memory.total / (1024 * 1024),
                "available_mb": memory.available / (1024 * 1024),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total / (1024 * 1024 * 1024),
                "free_gb": disk.free / (1024 * 1024 * 1024),
                "percent": disk.percent
            },
            "platform": platform.platform()
        }
        
        # Set warning if resources are low
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            health_data["components"]["system"]["status"] = "WARNING"
    except Exception as e:
        health_data["components"]["system"] = {
            "status": "ERROR",
            "message": str(e)
        }
    
    # Check data sources health
    try:
        with session_scope() as session:
            # Get data source status
            scraper_statuses = session.query(ScraperStatus).all()
            
            statuses = []
            for status in scraper_statuses:
                source = session.query(DataSource).filter_by(id=status.source_id).first()
                source_name = source.name if source else f"Unknown Source ({status.source_id})"
                
                statuses.append({
                    "source_id": status.source_id,
                    "source_name": source_name,
                    "status": status.status,
                    "last_check": status.last_check.isoformat() if status.last_check else None,
                    "last_success": status.last_success.isoformat() if status.last_success else None,
                    "error_count": status.error_count,
                    "message": status.message
                })
            
            health_data["components"]["data_sources"] = {
                "status": "OK",
                "sources": statuses
            }
            
            # Check if any data source has errors
            for status in statuses:
                if status["status"] != "OK" and status["status"] != "WARNING":
                    health_data["components"]["data_sources"]["status"] = "WARNING"
                    break
    except Exception as e:
        health_data["components"]["data_sources"] = {
            "status": "ERROR",
            "message": str(e)
        }
    
    # Set overall status
    if not overall_status:
        health_data["status"] = "ERROR"
    elif any(component["status"] == "ERROR" for component in health_data["components"].values()):
        health_data["status"] = "ERROR"
    elif any(component["status"] == "WARNING" for component in health_data["components"].values()):
        health_data["status"] = "WARNING"
    
    # Return health data with appropriate status code
    status_code = 200 if health_data["status"] != "ERROR" else 500
    return jsonify(health_data), status_code


@api.route('/data-sources', methods=['GET'])
def get_data_sources():
    """Get all data sources."""
    with session_scope() as session:
        try:
            sources = session.query(DataSource).all()
            result = []
            
            for source in sources:
                # Count proposals for this source
                proposal_count = session.query(func.count(Proposal.id)).filter(Proposal.source_id == source.id).scalar()
                
                result.append({
                    "id": source.id,
                    "name": source.name,
                    "url": source.url,
                    "description": source.description,
                    "last_scraped": source.last_scraped.isoformat() if source.last_scraped else None,
                    "proposalCount": proposal_count,
                    "last_checked": source.last_checked.isoformat() if hasattr(source, 'last_checked') and source.last_checked else None,
                    "status": source.status if hasattr(source, 'status') else "unknown"
                })
            
            return jsonify({"status": "success", "data": result})
        except Exception as e:
            current_app.logger.error(f"Error in get_data_sources: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/data-sources/<int:source_id>', methods=['PUT'])
def update_data_source(source_id):
    """Update a data source."""
    with session_scope() as session:
        try:
            # Find the data source
            source = session.query(DataSource).filter_by(id=source_id).first()
            if not source:
                raise ResourceNotFoundError(f"Data source with ID {source_id} not found")
            
            # Get request data
            data = request.json
            if not data:
                raise ValidationError("No data provided")
            
            # Update fields
            if 'name' in data:
                source.name = data['name']
            if 'url' in data:
                source.url = data['url']
            if 'description' in data:
                source.description = data['description']
            
            # Commit changes
            session.commit()
            
            # Return updated data source
            return jsonify({
                "status": "success",
                "data": {
                    "id": source.id,
                    "name": source.name,
                    "url": source.url,
                    "description": source.description,
                    "last_scraped": source.last_scraped.isoformat() if source.last_scraped else None
                }
            })
        except (ResourceNotFoundError, ValidationError) as e:
            return jsonify({"status": "error", "message": str(e)}), e.status_code
        except Exception as e:
            current_app.logger.error(f"Error in update_data_source: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/data-sources', methods=['POST'])
def create_data_source():
    """Create a new data source."""
    with session_scope() as session:
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
    with session_scope() as session:
        try:
            # Find the data source
            source = session.query(DataSource).filter_by(id=source_id).first()
            if not source:
                raise ResourceNotFoundError(f"Data source with ID {source_id} not found")
            
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
        except (ResourceNotFoundError, ValidationError) as e:
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
    with session_scope() as session:
        try:
            # Find the data source
            source = session.query(DataSource).filter_by(id=source_id).first()
            if not source:
                raise ResourceNotFoundError(f"Data source with ID {source_id} not found")
            
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
            
            # Start the scraper task
            task_name = 'src.background_tasks.scraper_tasks.force_collect_task'
            task = celery_app.send_task(task_name, args=[source_id])
            
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
        except ResourceNotFoundError as e:
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
    with session_scope() as session:
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
    with session_scope() as session:
        try:
            # Find the data source
            source = session.query(DataSource).filter_by(id=source_id).first()
            if not source:
                raise ResourceNotFoundError(f"Data source with ID {source_id} not found")
            
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
                    "message": status.error_message
                }
            }
            
            # Include subtask_id if it exists
            if hasattr(status, 'subtask_id') and status.subtask_id:
                response_data["data"]["subtask_id"] = status.subtask_id
            
            return jsonify(response_data)
            
        except ResourceNotFoundError as e:
            return jsonify({"status": "error", "message": str(e)}), 404
        except Exception as e:
            current_app.logger.error(f"Error in check_scraper_status: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/data-sources/<int:source_id>/health-check', methods=['POST'])
def trigger_health_check(source_id):
    """
    Trigger a health check for a data source.
    
    This endpoint starts a Celery task to check the health of a data source.
    It returns the task ID which can be used to check the status of the task.
    """
    with session_scope() as session:
        try:
            # Find the data source
            source = session.query(DataSource).filter_by(id=source_id).first()
            if not source:
                raise ResourceNotFoundError(f"Data source with ID {source_id} not found")
            
            # Determine which health check task to use based on the source name
            if "Acquisition Gateway" in source.name:
                task_name = 'src.background_tasks.health_check_tasks.check_acquisition_gateway_task'
            elif "SSA Contract Forecast" in source.name:
                task_name = 'src.background_tasks.health_check_tasks.check_ssa_contract_forecast_task'
            else:
                # Default to all scrapers task if source name doesn't match
                task_name = 'src.background_tasks.health_check_tasks.check_all_scrapers_task'
            
            task = celery_app.send_task(task_name, args=[])
            
            return jsonify({
                "status": "success",
                "message": f"Health check task started for source {source.name}",
                "data": {
                    "task_id": task.id,
                    "source_id": source_id,
                    "source_name": source.name
                }
            })
        except ResourceNotFoundError as e:
            return jsonify({"status": "error", "message": str(e)}), e.status_code
        except Exception as e:
            current_app.logger.error(f"Error in trigger_health_check: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500 