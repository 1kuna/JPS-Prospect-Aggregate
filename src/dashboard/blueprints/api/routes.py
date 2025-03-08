"""Routes for the API blueprint."""

from flask import jsonify, request, current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from . import api
from src.database.db import session_scope, get_session, close_session, Session, dispose_engine, reconnect
from src.database.models import Proposal, DataSource, ScraperStatus
import datetime
from src.exceptions import ValidationError, ResourceNotFoundError, DatabaseError
import os
import glob
import shutil
import threading
from src.database.init_db import init_database
from datetime import datetime
import time
import traceback
from sqlalchemy import desc, asc, or_, and_
from src.utils.db_utils import rebuild_database as rebuild_db_util
import math

# Helper function to format file size
def format_file_size(size_bytes):
    """Format file size in bytes to a human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

@api.route('/proposals')
def get_proposals():
    """API endpoint to get proposals with sorting and pagination."""
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
        
        current_app.logger.info(f"API: Processing request with page={page}, per_page={per_page}")
        
        with session_scope() as session:
            # Start building the query
            query = session.query(Proposal)
            
            # Apply sorting
            if sort_order == "asc":
                query = query.order_by(getattr(Proposal, sort_by).asc())
            else:
                query = query.order_by(getattr(Proposal, sort_by).desc())
            
            # Apply pagination
            total_count = query.count()
            current_app.logger.info(f"API: Total proposals count: {total_count}")
            
            query = query.limit(per_page).offset((page - 1) * per_page)
            
            # Execute query and format results
            proposals = query.all()
            current_app.logger.info(f"API: Retrieved {len(proposals)} proposals for page {page} with per_page={per_page}")
            
            if not proposals and page > 1:
                raise ResourceNotFoundError(f"No proposals found for page {page}")
            
            # Calculate total_pages correctly
            total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
            
            result = {
                "status": "success",
                "data": [p.to_dict() for p in proposals],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": total_pages
                }
            }
            
            return jsonify(result)
            
    except ValidationError as e:
        current_app.logger.warning(f"Validation error in get_proposals: {e.message}")
        return jsonify(e.to_dict()), e.status_code
        
    except ResourceNotFoundError as e:
        current_app.logger.info(f"Resource not found in get_proposals: {e.message}")
        return jsonify(e.to_dict()), e.status_code

@api.route('/sources')
def get_sources():
    """API endpoint to get a list of data sources."""
    try:
        with session_scope() as session:
            sources = session.query(DataSource).all()
            return jsonify({
                "status": "success",
                "data": [s.to_dict() for s in sources]
            })
    except Exception as e:
        current_app.logger.error(f"Error in get_sources: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve data sources",
            "error_code": "DATABASE_ERROR"
        }), 500

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

@api.route('/scraper-status/<int:source_id>/check', methods=['POST'])
def check_specific_scraper_health(source_id):
    """API endpoint to check the health of a specific scraper."""
    session = get_session()
    
    try:
        # Get the data source
        data_source = session.query(DataSource).filter(DataSource.id == source_id).first()
        
        if not data_source:
            return jsonify({"success": False, "error": f"No data source found with ID {source_id}"}), 404
        
        # Check if the URL is accessible
        import requests
        from datetime import datetime
        import time
        
        start_time = time.time()
        try:
            response = requests.get(data_source.url, timeout=10)
            status = "working" if response.status_code == 200 else "not_working"
            message = f"HTTP Status: {response.status_code}"
        except Exception as e:
            status = "not_working"
            message = str(e)
        
        response_time = time.time() - start_time
        
        # Log the status
        current_app.logger.info(f"Health check for source {source_id} ({data_source.name}): Status = {status}, Response time = {response_time:.2f}s")
        
        try:
            # Delete any existing status records for this source to avoid duplicates
            session.query(ScraperStatus).filter(ScraperStatus.source_id == source_id).delete()
            
            # Create a new scraper status record
            scraper_status = ScraperStatus(
                source_id=source_id,
                status=status,
                last_checked=datetime.utcnow(),
                error_message=message if status == "not_working" else None,
                response_time=response_time
            )
            session.add(scraper_status)
            
            # Commit the changes
            session.commit()
            
            # Verify the update
            updated_status = session.query(ScraperStatus).filter(ScraperStatus.source_id == source_id).first()
            if updated_status:
                current_app.logger.info(f"After commit: ScraperStatus for source {source_id}: Status = {updated_status.status}")
            else:
                current_app.logger.error(f"Failed to create ScraperStatus for source {source_id}")
                
            return jsonify({
                "success": True,
                "message": f"Health check completed for {data_source.name}",
                "status": status,
                "response_time": response_time
            })
        except Exception as db_error:
            import traceback
            current_app.logger.error(f"Database error during health check for source {source_id}: {db_error}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            session.rollback()
            return jsonify({
                "success": False,
                "error": f"Database error: {str(db_error)}"
            }), 500
    
    except Exception as e:
        current_app.logger.error(f"Error checking scraper health: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
    finally:
        close_session(session)

@api.route('/statistics')
def get_statistics():
    """API endpoint to get statistics about the proposals."""
    session = get_session()
    
    try:
        # Start with a base query
        base_query = session.query(Proposal)
        
        # Get total number of proposals
        total_proposals = base_query.count()
        
        # Get proposals by agency
        agency_query = session.query(
            Proposal.agency, 
            func.count(Proposal.id)
        )
        agency_counts = agency_query.group_by(Proposal.agency).all()
        
        # Get proposals by status
        status_query = session.query(
            Proposal.status, 
            func.count(Proposal.id)
        )
        status_counts = status_query.group_by(Proposal.status).all()
        
        # Get proposals by source
        source_query = session.query(
            DataSource.name, 
            func.count(Proposal.id)
        ).join(DataSource, Proposal.source_id == DataSource.id)
        source_counts = source_query.group_by(DataSource.name).all()
        
        # Get proposals by month
        month_query = session.query(
            func.strftime('%Y-%m', Proposal.release_date).label('month'),
            func.count(Proposal.id)
        )
        month_counts = month_query.group_by('month').order_by('month').all()
        
        # Format the results
        result = {
            "status": "success",
            "data": {
                "total_proposals": total_proposals,
                "by_agency": {agency: count for agency, count in agency_counts if agency},
                "by_status": {status: count for status, count in status_counts if status},
                "by_source": {source: count for source, count in source_counts if source},
                "by_month": {month: count for month, count in month_counts if month}
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in get_statistics: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve statistics",
            "error_code": "DATABASE_ERROR"
        }), 500
        
    finally:
        close_session(session)

@api.route('/dashboard')
def get_dashboard_data():
    """API endpoint to get dashboard data."""
    try:
        # Get pagination parameters
        try:
            per_page = int(request.args.get("per_page", 10))
            if per_page < 1 or per_page > 100:
                per_page = 10  # Default to 10 if invalid
        except ValueError:
            per_page = 10  # Default to 10 if not an integer
            
        try:
            page = int(request.args.get("page", 1))
            if page < 1:
                page = 1  # Default to first page if invalid
        except ValueError:
            page = 1  # Default to first page if not an integer
            
        current_app.logger.info(f"Dashboard API: page={page}, per_page={per_page}")
        
        with session_scope() as session:
            # Get total number of proposals
            total_proposals = session.query(Proposal).count()
            
            # Get number of active data sources
            active_sources = session.query(DataSource).count()
            
            # Get last scrape time
            last_scrape = session.query(func.max(DataSource.last_scraped)).scalar()
            
            # Build query for proposals
            query = session.query(Proposal)
            
            # Apply sorting (default to newest first)
            query = query.order_by(Proposal.release_date.desc())
            
            # Get total count for pagination
            total_count = query.count()
            
            # Apply pagination
            proposals = query.limit(per_page).offset((page - 1) * per_page).all()
            
            # Calculate total_pages correctly
            total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
            
            # Format the results
            result = {
                "status": "success",
                "total_proposals": total_proposals,
                "active_sources": active_sources,
                "last_scrape": last_scrape.isoformat() if last_scrape else None,
                "proposals": [p.to_dict() for p in proposals],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": total_pages
                }
            }
            
            return jsonify(result)
            
    except Exception as e:
        current_app.logger.error(f"Error in get_dashboard_data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve dashboard data",
            "error_code": "DATABASE_ERROR"
        }), 500

@api.route('/data-sources')
def get_data_sources():
    """API endpoint to get all data sources."""
    try:
        with session_scope() as session:
            # Get all data sources
            sources = session.query(DataSource).all()
            
            # Format the data sources
            sources_data = []
            for s in sources:
                try:
                    # Get the latest scraper status for this source
                    status = session.query(ScraperStatus).filter(ScraperStatus.source_id == s.id).order_by(ScraperStatus.last_checked.desc()).first()
                    
                    # Log the status
                    status_value = status.status if status else "unknown"
                    current_app.logger.info(f"Data source {s.id} ({s.name}): Status = {status_value}")
                    
                    # Get the count of proposals for this source
                    proposal_count = session.query(func.count(Proposal.id)).filter(Proposal.source_id == s.id).scalar()
                    
                    sources_data.append({
                        "id": s.id,
                        "name": s.name,
                        "url": s.url,
                        "description": s.description,
                        "lastScraped": s.last_scraped.isoformat() if s.last_scraped else None,
                        "status": status_value,
                        "lastChecked": status.last_checked.isoformat() if status and status.last_checked else None,
                        "proposalCount": proposal_count
                    })
                except Exception as source_error:
                    current_app.logger.error(f"Error processing data source {s.id} ({s.name}): {source_error}")
                    # Add the source with default values for the problematic fields
                    sources_data.append({
                        "id": s.id,
                        "name": s.name,
                        "url": s.url,
                        "description": s.description,
                        "lastScraped": s.last_scraped.isoformat() if s.last_scraped else None,
                        "status": "unknown",
                        "lastChecked": None,
                        "proposalCount": 0
                    })
            
            # Return the data sources
            return jsonify(sources_data)
            
    except Exception as e:
        current_app.logger.error(f"Error getting data sources: {e}")
        return jsonify({
            "status": "error",
            "message": "Error loading data sources. Please try again."
        }), 500

@api.route('/data-sources/collect-all', methods=['POST'])
def collect_all_sources():
    """API endpoint to force collection from all data sources."""
    try:
        # Import the Celery task
        from src.tasks.scraper_tasks import force_collect_task
        
        # Run the task with source_id=None to collect from all sources, but don't wait for it to complete
        task = force_collect_task.delay(source_id=None)
        
        # Return the task ID so the client can check the status later
        return jsonify({
            "success": True,
            "message": "Collection started",
            "task_id": task.id
        })
            
    except Exception as e:
        current_app.logger.error(f"Error starting collection from all sources: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api.route('/init-db', methods=['POST'])
def initialize_db():
    """API endpoint to initialize the database."""
    try:
        # Run the database initialization in a background thread
        def init_and_reconnect():
            try:
                # Initialize the database
                current_app.logger.info("Starting database initialization process")
                init_database()
                
                # Wait a moment for the initialization to complete
                import time
                time.sleep(2)
                
                # Try to reconnect to the database
                reconnect()
                current_app.logger.info("Database initialization completed successfully")
            except Exception as e:
                error_msg = f"Error during database initialization: {str(e)}"
                current_app.logger.error(error_msg)
                # Log the full traceback for debugging
                import traceback
                current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        thread = threading.Thread(target=init_and_reconnect)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Database initialization started"
        })
    except Exception as e:
        current_app.logger.error(f"Error starting initialization thread: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error starting initialization thread: {str(e)}"
        }), 500

@api.route('/database-backups')
def get_database_backups():
    """API endpoint to get a list of database backups."""
    try:
        # Get the database directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        db_dir = os.path.join(project_root, 'data')
        
        # Get a list of backup files
        backup_files = []
        for file in os.listdir(db_dir):
            if file.startswith('jps_database_backup_') and file.endswith('.db'):
                file_path = os.path.join(db_dir, file)
                backup_files.append({
                    'filename': file,
                    'size': os.path.getsize(file_path),
                    'created': os.path.getctime(file_path)
                })
        
        # Sort by creation time (newest first)
        backup_files.sort(key=lambda x: x['created'], reverse=True)
        
        # Format the dates
        for backup in backup_files:
            backup['created'] = datetime.fromtimestamp(backup['created']).isoformat()
            backup['size_formatted'] = format_file_size(backup['size'])
        
        return jsonify(backup_files)
    
    except Exception as e:
        current_app.logger.error(f"Error getting database backups: {e}")
        return jsonify({
            "error": str(e)
        }), 500

@api.route('/database-backups/cleanup', methods=['POST'])
def cleanup_database_backups():
    """API endpoint to clean up old database backups."""
    try:
        # Get the database directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        db_dir = os.path.join(project_root, 'data')
        
        # Get the maximum number of backups to keep
        data = request.get_json()
        max_backups = data.get('max_backups', 5)
        
        # Validate the input
        if not isinstance(max_backups, int) or max_backups < 1:
            return jsonify({
                "status": "error",
                "message": "Invalid max_backups parameter. Must be a positive integer."
            }), 400
        
        # Find all database backup files
        backup_pattern = os.path.join(db_dir, 'proposals_backup_*.db')
        backup_files = glob.glob(backup_pattern)
        
        # Sort files by modification time (newest first)
        backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Keep only the specified number of most recent backups
        files_to_delete = backup_files[max_backups:]
        
        # Delete old backups
        for old_backup in files_to_delete:
            try:
                os.remove(old_backup)
                current_app.logger.info(f"Deleted old backup: {old_backup}")
            except Exception as e:
                current_app.logger.warning(f"Could not delete old backup {old_backup}: {e}")
        
        # Get the updated list of backups
        remaining_backups = glob.glob(backup_pattern)
        remaining_backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Format the response
        backups_info = []
        for backup in remaining_backups:
            backup_name = os.path.basename(backup)
            backup_size = os.path.getsize(backup)
            backup_date = datetime.fromtimestamp(os.path.getmtime(backup))
            
            backups_info.append({
                "name": backup_name,
                "size": format_file_size(backup_size),
                "date": backup_date.isoformat()
            })
        
        return jsonify({
            "status": "success",
            "message": f"Successfully cleaned up database backups. Kept {len(remaining_backups)} most recent backups.",
            "backups": backups_info
        })
    except Exception as e:
        current_app.logger.error(f"Error cleaning up database backups: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error cleaning up database backups: {str(e)}"
        }), 500

@api.route('/reset-everything', methods=['POST'])
def reset_everything():
    """API endpoint to reset everything (downloads and database)."""
    try:
        # Close any existing database connections
        try:
            # Close all existing connections
            Session.remove()
            dispose_engine()
        except Exception as e:
            current_app.logger.warning(f"Error closing database connections: {e}")
        
        # Run the reset in a background thread
        def reset_and_reconnect():
            try:
                # Get the project root directory
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
                
                # Delete all downloaded files
                downloads_dir = os.path.join(project_root, 'downloads')
                if os.path.exists(downloads_dir):
                    current_app.logger.info(f"Deleting downloads directory: {downloads_dir}")
                    shutil.rmtree(downloads_dir)
                    os.makedirs(downloads_dir, exist_ok=True)
                
                # Delete all database backups
                db_dir = os.path.join(project_root, 'data')
                backup_pattern = os.path.join(db_dir, 'proposals_backup_*.db')
                backup_files = glob.glob(backup_pattern)
                for backup in backup_files:
                    current_app.logger.info(f"Deleting database backup: {backup}")
                    os.remove(backup)
                
                # Delete the database file
                db_file = os.path.join(db_dir, 'proposals.db')
                if os.path.exists(db_file):
                    current_app.logger.info(f"Deleting database file: {db_file}")
                    os.remove(db_file)
                
                # Recreate the database
                current_app.logger.info("Recreating database...")
                init_database()
                
                # Reconnect to the database
                current_app.logger.info("Reconnecting to database...")
                reconnect()
                
                current_app.logger.info("Reset completed successfully.")
            except Exception as e:
                current_app.logger.error(f"Error during reset: {e}")
                # Try to reconnect to the database even if there was an error
                try:
                    reconnect()
                except Exception as reconnect_error:
                    current_app.logger.error(f"Error reconnecting to database: {reconnect_error}")
        
        # Start the reset thread
        reset_thread = threading.Thread(target=reset_and_reconnect)
        reset_thread.daemon = True
        reset_thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Reset process started. This may take a few minutes."
        })
    except Exception as e:
        current_app.logger.error(f"Error starting reset process: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error starting reset process: {str(e)}"
        }), 500

@api.route('/data-sources/<int:source_id>/collect', methods=['POST'])
def collect_source(source_id):
    """API endpoint to force collection from a specific data source."""
    try:
        # Import the Celery task
        from src.tasks.scraper_tasks import force_collect_task
        
        # Run the task with the specified source_id, but don't wait for it to complete
        task = force_collect_task.delay(source_id=source_id)
        
        # Get the source name
        with session_scope() as session:
            source = session.query(DataSource).filter(DataSource.id == source_id).first()
            source_name = source.name if source else f"Source ID {source_id}"
        
        # Return the task ID so the client can check the status later
        return jsonify({
            "success": True,
            "message": f"Collection started for {source_name}",
            "task_id": task.id,
            "source_name": source_name
        })
            
    except Exception as e:
        current_app.logger.error(f"Error starting collection from source {source_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """API endpoint to check the status of a Celery task."""
    try:
        # Import the Celery app
        from src.celery_app import celery_app
        
        # Get the task
        task = celery_app.AsyncResult(task_id)
        
        # Check if the task exists
        if not task:
            return jsonify({
                "success": False,
                "error": f"Task with ID {task_id} not found"
            }), 404
        
        # Check the task state
        if task.state == 'PENDING':
            # Task is pending
            response = {
                "success": True,
                "state": task.state,
                "status": "pending",
                "info": "Task is pending execution"
            }
        elif task.state == 'STARTED':
            # Task is running
            response = {
                "success": True,
                "state": task.state,
                "status": "in_progress",
                "info": "Task is in progress"
            }
        elif task.state == 'SUCCESS':
            # Task completed successfully
            result = task.result
            response = {
                "success": True,
                "state": task.state,
                "status": "completed",
                "result": result
            }
        elif task.state == 'FAILURE':
            # Task failed
            response = {
                "success": False,
                "state": task.state,
                "status": "failed",
                "error": str(task.result)
            }
        else:
            # Other states (REVOKED, RETRY, etc.)
            response = {
                "success": True,
                "state": task.state,
                "status": "unknown",
                "info": f"Task is in state: {task.state}"
            }
        
        return jsonify(response)
            
    except Exception as e:
        current_app.logger.error(f"Error checking task status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api.route('/debug/scraper-status', methods=['GET'])
def debug_scraper_status():
    """API endpoint to debug scraper status."""
    session = get_session()
    
    try:
        # Get all scraper statuses
        statuses = session.query(ScraperStatus).all()
        
        # Format the statuses
        status_data = []
        for status in statuses:
            status_data.append({
                "id": status.id,
                "source_id": status.source_id,
                "status": status.status,
                "last_checked": status.last_checked.isoformat() if status.last_checked else None,
                "error_message": status.error_message,
                "response_time": status.response_time
            })
        
        return jsonify(status_data)
    
    except Exception as e:
        current_app.logger.error(f"Error getting scraper status: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        close_session(session)

@api.route('/scraper-status/initialize', methods=['POST'])
def initialize_scraper_status():
    """API endpoint to initialize scraper status for all data sources."""
    session = get_session()
    
    try:
        # Get all data sources
        data_sources = session.query(DataSource).all()
        
        # Initialize status for each data source
        initialized_count = 0
        for source in data_sources:
            # Check if a status record already exists
            existing_status = session.query(ScraperStatus).filter(ScraperStatus.source_id == source.id).first()
            
            if not existing_status:
                # Create a new status record with default values
                new_status = ScraperStatus(
                    source_id=source.id,
                    status="unknown",
                    last_checked=None,
                    error_message=None,
                    response_time=None
                )
                session.add(new_status)
                initialized_count += 1
        
        # Commit the changes
        session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Initialized scraper status for {initialized_count} data sources"
        })
    
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error initializing scraper status: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    
    finally:
        close_session(session)

@api.route('/rebuild-db', methods=['POST'])
def rebuild_database():
    """API endpoint to trigger database rebuild."""
    try:
        # Run the database rebuild in a background thread
        def rebuild_and_reconnect():
            try:
                # Import the rebuild function
                from src.utils.db_utils import rebuild_database as rebuild_db
                
                # Rebuild the database
                current_app.logger.info("Starting database rebuild process")
                rebuild_db()
                
                # Wait a moment for the rebuild to complete
                import time
                time.sleep(2)
                
                # Try to reconnect to the database
                reconnect()
                current_app.logger.info("Database rebuild completed successfully")
            except Exception as e:
                error_msg = f"Error during database rebuild: {str(e)}"
                current_app.logger.error(error_msg)
                # Log the full traceback for debugging
                import traceback
                current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        thread = threading.Thread(target=rebuild_and_reconnect)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Database rebuild started"
        })
    except Exception as e:
        current_app.logger.error(f"Error starting rebuild thread: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error starting rebuild: {str(e)}"
        }), 500 