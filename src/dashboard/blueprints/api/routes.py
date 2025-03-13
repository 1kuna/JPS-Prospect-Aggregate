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
import traceback

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

@api.route('/data-sources/<int:source_id>/pull', methods=['POST'])
def pull_data_source(source_id):
    """API endpoint to pull/scrape a data source."""
    with session_scope() as session:
        source = session.query(DataSource).filter(DataSource.id == source_id).first()
        if not source:
            raise ResourceNotFoundError(f"Data source with ID {source_id} not found")
        
        current_app.logger.info(f"API: Pulling data from source {source.name} (ID: {source_id})")
        
        # First, check if Playwright is installed and browsers are available
        try:
            from playwright.sync_api import sync_playwright
            # Try to initialize Playwright and check browser availability
            with sync_playwright() as playwright:
                # Check if chromium is installed by trying to launch it
                try:
                    browser = playwright.chromium.launch()
                    browser.close()
                    current_app.logger.info("Playwright and browsers are properly installed")
                except Exception as browser_error:
                    current_app.logger.error(f"Playwright browser error: {str(browser_error)}")
                    # This is likely a browser installation issue
                    return jsonify({
                        "status": "error",
                        "message": "Playwright browsers not installed. Please run 'playwright install'"
                    }), 500
        except ImportError:
            current_app.logger.error("Playwright package not installed")
            return jsonify({
                "status": "error",
                "message": "Playwright not installed. Please run 'pip install playwright' and 'playwright install'"
            }), 500
        except Exception as e:
            current_app.logger.error(f"Error initializing Playwright: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Error initializing Playwright: {str(e)}. Make sure browsers are installed with 'playwright install'"
            }), 500
        
        # Run the appropriate scraper based on the data source name
        if source.name == "Acquisition Gateway Forecast":
            try:
                # Import the check_url_accessibility function
                from src.scrapers.acquisition_gateway import check_url_accessibility, ACQUISITION_GATEWAY_URL, run_scraper
                import threading
                import queue
                import time
                
                # Check if the URL is accessible
                if not check_url_accessibility(ACQUISITION_GATEWAY_URL):
                    return jsonify({
                        "status": "error",
                        "message": f"The URL {ACQUISITION_GATEWAY_URL} is not accessible. Please check your internet connection or if the website is down."
                    }), 500
                
                # Create a queue to get the result from the thread
                result_queue = queue.Queue()
                
                # Run the scraper in a separate thread to avoid blocking the response
                def run_scraper_thread():
                    try:
                        success = run_scraper(force=True)
                        current_app.logger.info(f"Scraper completed with success={success}")
                        # Put the result in the queue
                        result_queue.put(("success", success))
                    except Exception as e:
                        current_app.logger.error(f"Error in scraper thread: {str(e)}")
                        current_app.logger.error(traceback.format_exc())
                        # Put the error in the queue
                        result_queue.put(("error", str(e)))
                
                # Create and start the thread
                thread = threading.Thread(target=run_scraper_thread)
                thread.daemon = True
                thread.start()
                
                # Store the thread and start time in the application context for status checking
                if not hasattr(current_app, 'scraper_threads'):
                    current_app.scraper_threads = {}
                
                current_app.scraper_threads[source_id] = {
                    'thread': thread,
                    'start_time': time.time(),
                    'source_name': source.name,
                    'status': 'running',
                    'result_queue': result_queue
                }
                
                return jsonify({
                    "status": "success",
                    "message": f"Started pulling data from {source.name}. This may take a while...",
                    "job_id": source_id
                })
            except Exception as e:
                current_app.logger.error(f"Error running Acquisition Gateway scraper: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                return jsonify({
                    "status": "error",
                    "message": f"Error running scraper: {str(e)}"
                }), 500
        elif source.name == "SSA Contract Forecast":
            try:
                # Import the check_url_accessibility function
                from src.scrapers.ssa_contract_forecast import check_url_accessibility, SSA_CONTRACT_FORECAST_URL, run_scraper
                import threading
                import queue
                import time
                
                # Check if the URL is accessible
                if not check_url_accessibility(SSA_CONTRACT_FORECAST_URL):
                    return jsonify({
                        "status": "error",
                        "message": f"The URL {SSA_CONTRACT_FORECAST_URL} is not accessible. Please check your internet connection or if the website is down."
                    }), 500
                
                # Create a queue to get the result from the thread
                result_queue = queue.Queue()
                
                # Run the scraper in a separate thread to avoid blocking the response
                def run_scraper_thread():
                    try:
                        success = run_scraper(force=True)
                        current_app.logger.info(f"Scraper completed with success={success}")
                        # Put the result in the queue
                        result_queue.put(("success", success))
                    except Exception as e:
                        current_app.logger.error(f"Error in scraper thread: {str(e)}")
                        current_app.logger.error(traceback.format_exc())
                        # Put the error in the queue
                        result_queue.put(("error", str(e)))
                
                # Create and start the thread
                thread = threading.Thread(target=run_scraper_thread)
                thread.daemon = True
                thread.start()
                
                # Store the thread and start time in the application context for status checking
                if not hasattr(current_app, 'scraper_threads'):
                    current_app.scraper_threads = {}
                
                current_app.scraper_threads[source_id] = {
                    'thread': thread,
                    'start_time': time.time(),
                    'source_name': source.name,
                    'status': 'running',
                    'result_queue': result_queue
                }
                
                return jsonify({
                    "status": "success",
                    "message": f"Started pulling data from {source.name}. This may take a while...",
                    "job_id": source_id
                })
            except Exception as e:
                current_app.logger.error(f"Error running SSA Contract Forecast scraper: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                return jsonify({
                    "status": "error",
                    "message": f"Error running scraper: {str(e)}"
                }), 500
        else:
            return jsonify({
                "status": "error",
                "message": f"Unknown data source: {source.name}"
            }), 400

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

@api.route('/data-sources/<int:source_id>/status', methods=['GET'])
def check_scraper_status(source_id):
    """API endpoint to check the status of a scraper job."""
    import time
    
    # Check if the scraper thread exists
    if not hasattr(current_app, 'scraper_threads') or source_id not in current_app.scraper_threads:
        return jsonify({
            "status": "unknown",
            "message": "No scraper job found for this data source"
        })
    
    # Get the scraper thread info
    scraper_info = current_app.scraper_threads[source_id]
    thread = scraper_info['thread']
    start_time = scraper_info['start_time']
    source_name = scraper_info['source_name']
    result_queue = scraper_info['result_queue']
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Check if the thread is still alive
    if not thread.is_alive():
        # Thread has completed, check the result
        try:
            # Get the result from the queue if available
            if not result_queue.empty():
                result_type, result_value = result_queue.get(block=False)
                if result_type == "success":
                    # Update the status
                    scraper_info['status'] = 'completed'
                    return jsonify({
                        "status": "completed",
                        "message": f"Scraper for {source_name} completed successfully",
                        "elapsed_time": elapsed_time
                    })
                else:
                    # Error occurred
                    scraper_info['status'] = 'failed'
                    return jsonify({
                        "status": "failed",
                        "message": f"Scraper for {source_name} failed: {result_value}",
                        "elapsed_time": elapsed_time
                    })
            else:
                # Thread completed but no result in queue (unusual)
                scraper_info['status'] = 'completed'
                return jsonify({
                    "status": "completed",
                    "message": f"Scraper for {source_name} completed but no result available",
                    "elapsed_time": elapsed_time
                })
        except Exception as e:
            current_app.logger.error(f"Error checking scraper result: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Error checking scraper result: {str(e)}",
                "elapsed_time": elapsed_time
            })
    
    # Thread is still running, check for timeout
    timeout_seconds = 180  # 3 minutes timeout (increased from 60 seconds)
    if elapsed_time > timeout_seconds:
        # Mark as timed out
        scraper_info['status'] = 'timeout'
        
        # Try to terminate the thread (though Python threads can't be forcibly terminated)
        # At least we can mark it as timed out for the UI
        current_app.logger.warning(f"Scraper for {source_name} timed out after {elapsed_time:.1f} seconds")
        
        # Update the status in the database
        try:
            with session_scope() as session:
                data_source = session.query(DataSource).filter_by(id=source_id).first()
                if data_source:
                    status_record = session.query(ScraperStatus).filter_by(source_id=source_id).first()
                    if status_record:
                        status_record.status = "error"
                        status_record.error_message = f"Scraper timed out after {elapsed_time:.1f} seconds"
                        status_record.last_checked = datetime.datetime.utcnow()
                        session.commit()
                        current_app.logger.info(f"Updated status record for {source_name} to error due to timeout")
        except Exception as e:
            current_app.logger.error(f"Error updating status record: {str(e)}")
        
        return jsonify({
            "status": "timeout",
            "message": f"Scraper for {source_name} timed out after {elapsed_time:.1f} seconds",
            "elapsed_time": elapsed_time
        })
    
    # Still running and within timeout
    return jsonify({
        "status": "running",
        "message": f"Scraper for {source_name} is still running ({elapsed_time:.1f} seconds elapsed)",
        "elapsed_time": elapsed_time
    }) 