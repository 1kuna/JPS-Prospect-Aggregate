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

@api.route('/dashboard')
def get_dashboard_data():
    """API endpoint to get dashboard data."""
    try:
        with session_scope() as session:
            # Get total number of proposals
            total_proposals = session.query(Proposal).count()
            
            # Get number of active data sources
            active_sources = session.query(DataSource).count()
            
            # Get last scrape time
            last_scrape = session.query(func.max(DataSource.last_scraped)).scalar()
            
            # Get recent proposals (limit to 10)
            recent_proposals = session.query(Proposal).order_by(Proposal.imported_at.desc()).limit(10).all()
            
            # Format the proposals
            proposals_data = []
            for p in recent_proposals:
                proposals_data.append({
                    "id": p.id,
                    "title": p.title,
                    "agency": p.agency,
                    "source": p.source.name if p.source else None,
                    "date": p.release_date.isoformat() if p.release_date else None,
                    "status": p.status
                })
            
            # Return the dashboard data
            return jsonify({
                "totalProposals": total_proposals,
                "activeSources": active_sources,
                "lastScrape": last_scrape.isoformat() if last_scrape else None,
                "proposals": proposals_data
            })
            
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard data: {e}")
        return jsonify({
            "status": "error",
            "message": "Error loading proposals. Please try again."
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
                # Get the latest scraper status for this source
                status = session.query(ScraperStatus).filter(ScraperStatus.source_id == s.id).order_by(ScraperStatus.last_checked.desc()).first()
                
                # Get the count of proposals for this source
                proposal_count = session.query(func.count(Proposal.id)).filter(Proposal.source_id == s.id).scalar()
                
                sources_data.append({
                    "id": s.id,
                    "name": s.name,
                    "url": s.url,
                    "description": s.description,
                    "lastScraped": s.last_scraped.isoformat() if s.last_scraped else None,
                    "status": status.status if status else "unknown",
                    "proposalCount": proposal_count
                })
            
            # Return the data sources
            return jsonify(sources_data)
            
    except Exception as e:
        current_app.logger.error(f"Error getting data sources: {e}")
        return jsonify({
            "status": "error",
            "message": "Error loading data sources. Please try again."
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
    """API endpoint to get all database backups."""
    try:
        # Get the database directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        db_dir = os.path.join(project_root, 'data')
        
        # Find all database backup files
        backup_pattern = os.path.join(db_dir, 'proposals_backup_*.db')
        backup_files = glob.glob(backup_pattern)
        
        # Sort files by modification time (newest first)
        backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Prepare the list of backups with details
        backups = []
        for backup in backup_files:
            size_bytes = os.path.getsize(backup)
            size_mb = size_bytes / (1024 * 1024)
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(backup))
            backups.append({
                'file': os.path.basename(backup),
                'size': f"{size_mb:.2f} MB",
                'created': mod_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return jsonify({
            "status": "success",
            "backups": backups
        })
    except Exception as e:
        current_app.logger.error(f"Error getting database backups: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error getting database backups: {str(e)}"
        }), 500

@api.route('/database-backups/cleanup', methods=['POST'])
def cleanup_database_backups():
    """API endpoint to clean up old database backups."""
    try:
        # Get the maximum number of backups to keep
        data = request.get_json()
        max_backups = data.get('max_backups', 5)
        
        # Validate the input
        if not isinstance(max_backups, int) or max_backups < 1:
            return jsonify({
                "status": "error",
                "message": "Invalid max_backups parameter. Must be a positive integer."
            }), 400
        
        # Get the database directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        db_dir = os.path.join(project_root, 'data')
        
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
        remaining_backup_files = glob.glob(backup_pattern)
        remaining_backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Prepare the list of remaining backups with details
        backups = []
        for backup in remaining_backup_files:
            size_bytes = os.path.getsize(backup)
            size_mb = size_bytes / (1024 * 1024)
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(backup))
            backups.append({
                'file': os.path.basename(backup),
                'size': f"{size_mb:.2f} MB",
                'created': mod_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return jsonify({
            "status": "success",
            "message": f"Cleaned up old backups. Kept {len(backups)} most recent backups.",
            "backups": backups
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
                
                # Delete the current database
                db_path = os.path.join(db_dir, 'proposals.db')
                if os.path.exists(db_path):
                    current_app.logger.info(f"Deleting database: {db_path}")
                    os.remove(db_path)
                
                # Create a new empty database
                current_app.logger.info("Creating new empty database")
                init_database()
                
                # Wait a moment for the reset to complete
                import time
                time.sleep(2)
                
                # Try to reconnect to the database
                reconnect()
                current_app.logger.info("Reset completed successfully")
            except Exception as e:
                error_msg = f"Error during reset: {str(e)}"
                current_app.logger.error(error_msg)
                # Log the full traceback for debugging
                import traceback
                current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        thread = threading.Thread(target=reset_and_reconnect)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Reset started"
        })
    except Exception as e:
        current_app.logger.error(f"Error starting reset thread: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error starting reset thread: {str(e)}"
        }), 500 