import os
import sys
import threading
import datetime
import shutil
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from sqlalchemy import func
import logging
from logging.handlers import RotatingFileHandler

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'app.log')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.db import get_session, close_session, engine, Session, dispose_engine
from src.database.models import Proposal, DataSource, ScraperStatus
from src.scrapers.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from src.scrapers.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper
from src.database.init_db import init_database

# Import the rebuild_database function
from scripts.rebuild_db import rebuild_database, list_backups, cleanup_old_backups

# Load environment variables
load_dotenv()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure the app
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24).hex())
    
    # Register routes
    
    @app.route("/")
    def index():
        """Render the dashboard homepage"""
        return render_template("index.html")
    
    @app.route("/data-sources")
    def data_sources():
        """Render the data sources page"""
        return render_template("data_sources.html")
    
    @app.route("/api/proposals")
    def get_proposals():
        """API endpoint to get proposals with filtering and sorting"""
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
    
    @app.route("/api/sources")
    def get_sources():
        """API endpoint to get all data sources"""
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
            app.logger.error(f"Error getting sources: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            close_session(session)
    
    @app.route("/api/filters")
    def get_filters():
        """API endpoint to get filter options"""
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
    
    @app.route("/api/rebuild-db", methods=["POST"])
    def rebuild_db():
        """API endpoint to trigger database rebuild"""
        # Close any existing database connections
        
        try:
            # Close all existing connections
            Session.remove()
            dispose_engine()
        except Exception as e:
            app.logger.warning(f"Error closing database connections: {e}")
            return jsonify({
                "status": "error",
                "message": f"Error closing database connections: {str(e)}"
            }), 500
        
        # Run the database rebuild in a background thread
        def rebuild_and_reconnect():
            try:
                # Rebuild the database
                app.logger.info("Starting database rebuild process")
                rebuild_database()
                
                # Wait a moment for the rebuild to complete
                import time
                time.sleep(2)
                
                # Try to reconnect to the database
                from src.database.db import reconnect
                reconnect()
                app.logger.info("Database rebuild completed successfully")
            except Exception as e:
                error_msg = f"Error during database rebuild: {str(e)}"
                app.logger.error(error_msg)
                # Log the full traceback for debugging
                import traceback
                app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        try:
            thread = threading.Thread(target=rebuild_and_reconnect)
            thread.daemon = True
            thread.start()
            
            # Return success response
            return jsonify({
                "status": "success", 
                "message": "Database rebuild initiated. The application may need to be restarted to use the new database."
            })
        except Exception as e:
            app.logger.error(f"Error starting rebuild thread: {e}")
            return jsonify({
                "status": "error",
                "message": f"Error starting rebuild process: {str(e)}"
            }), 500
    
    @app.route("/api/reconnect-db", methods=["POST"])
    def reconnect_db():
        """API endpoint to reconnect to the database"""
        from src.database.db import reconnect
        
        success = reconnect()
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Successfully reconnected to the database"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to reconnect to the database"
            }), 500
    
    @app.route("/api/init-db", methods=["POST"])
    def init_db():
        """API endpoint to initialize the database"""
        try:
            logger.info("Starting database initialization...")
            
            # Get the database path
            database_url = os.getenv("DATABASE_URL", "sqlite:///data/proposals.db")
            db_path = database_url.replace("sqlite:///", "")
            logger.info(f"Database path: {db_path}")
            
            # Ensure the data directory exists
            data_dir = os.path.dirname(db_path)
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                logger.info(f"Created data directory: {data_dir}")
            
            # Check if database exists
            if os.path.exists(db_path):
                logger.info("Existing database found, attempting to close connections...")
                # Close any existing connections
                try:
                    Session.remove()
                    dispose_engine()
                    logger.info("Successfully closed database connections")
                except Exception as e:
                    logger.warning(f"Error closing database connections: {e}")
                
                # Delete the existing database
                try:
                    os.remove(db_path)
                    logger.info(f"Removed existing database: {db_path}")
                except Exception as e:
                    error_msg = f"Error removing existing database: {str(e)}"
                    logger.error(error_msg)
                    return jsonify({
                        "success": False,
                        "error": error_msg
                    }), 500
            
            # Initialize the database
            try:
                logger.info("Calling init_database()...")
                init_database()
                logger.info("Database initialized successfully")
                return jsonify({
                    "success": True,
                    "message": "Database initialized successfully"
                })
            except Exception as e:
                error_msg = f"Error during database initialization: {str(e)}"
                logger.error(error_msg)
                # Log the full traceback for debugging
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return jsonify({
                    "success": False,
                    "error": error_msg
                }), 500
            
        except Exception as e:
            error_msg = f"Unexpected error during database initialization: {str(e)}"
            logger.error(error_msg)
            # Log the full traceback for debugging
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 500
    
    @app.route("/api/stats")
    def get_stats():
        """API endpoint to get statistics about the data"""
        session = get_session()
        
        try:
            # Get counts by source
            source_counts = session.query(
                DataSource.id,
                DataSource.name,
                func.count(Proposal.id).label('count')
            ).outerjoin(
                Proposal, DataSource.id == Proposal.source_id
            ).group_by(
                DataSource.id, DataSource.name
            ).all()
            
            # Get total count
            total_count = session.query(func.count(Proposal.id)).scalar()
            
            # Get counts by agency (top 10)
            agency_counts = session.query(
                Proposal.agency,
                func.count(Proposal.id).label('count')
            ).filter(
                Proposal.agency != None
            ).group_by(
                Proposal.agency
            ).order_by(
                func.count(Proposal.id).desc()
            ).limit(10).all()
            
            # Get counts by status
            status_counts = session.query(
                Proposal.status,
                func.count(Proposal.id).label('count')
            ).filter(
                Proposal.status != None
            ).group_by(
                Proposal.status
            ).order_by(
                func.count(Proposal.id).desc()
            ).all()
            
            # Format the results
            result = {
                "total_proposals": total_count,
                "by_source": [
                    {"id": src[0], "name": src[1], "count": src[2]}
                    for src in source_counts
                ],
                "by_agency": [
                    {"agency": agency[0], "count": agency[1]}
                    for agency in agency_counts
                ],
                "by_status": [
                    {"status": status[0], "count": status[1]}
                    for status in status_counts
                ]
            }
            
            return jsonify(result)
        
        finally:
            close_session(session)
    
    @app.route("/api/check-updates")
    def check_updates():
        """API endpoint to check if new data is available"""
        session = get_session()
        
        try:
            # Get the last time data was refreshed - use a lightweight query
            last_refresh = session.query(func.max(DataSource.last_scraped)).scalar()
            
            # If there's no last_refresh timestamp, return no updates available
            if not last_refresh:
                return jsonify({
                    "updates_available": False, 
                    "last_refresh": None
                })
            
            # Get the last time the user checked for updates (from query parameter)
            last_check = request.args.get('last_check')
            
            if last_check:
                # Convert last_check to datetime
                try:
                    last_check_dt = datetime.datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                    
                    # Add a small buffer (5 seconds) to account for clock differences
                    buffer_time = datetime.timedelta(seconds=5)
                    adjusted_last_check = last_check_dt + buffer_time
                    
                    # Compare timestamps - only consider updates available if the difference is significant
                    # This prevents false positives due to small clock differences
                    if last_refresh > adjusted_last_check:
                        # Calculate time difference in seconds
                        time_diff = (last_refresh - last_check_dt).total_seconds()
                        
                        # Only show updates if the difference is more than our buffer
                        if time_diff > 5:
                            return jsonify({"updates_available": True, "last_refresh": last_refresh.isoformat()})
                        else:
                            # The timestamps are too close, likely just clock differences
                            return jsonify({"updates_available": False, "last_refresh": last_refresh.isoformat()})
                    else:
                        return jsonify({"updates_available": False, "last_refresh": last_refresh.isoformat()})
                except Exception as e:
                    # Log the error
                    app.logger.error(f"Error parsing date in check_updates: {e}")
                    # If there's an error parsing the date, assume no updates are available
                    # This is safer than showing false positives
                    return jsonify({"updates_available": False, "last_refresh": last_refresh.isoformat()})
            
            # Default response
            return jsonify({
                "updates_available": False, 
                "last_refresh": last_refresh.isoformat()
            })
        
        finally:
            close_session(session)
    
    @app.route("/api/data-sources")
    def get_data_sources():
        """API endpoint to get all data sources"""
        session = get_session()
        
        try:
            # Get all data sources
            sources = session.query(DataSource).all()
            
            # Format the response
            sources_data = []
            for source in sources:
                # Count proposals for this source
                proposal_count = session.query(func.count(Proposal.id)).filter(
                    Proposal.source_id == source.id,
                    Proposal.is_latest == True
                ).scalar()
                
                sources_data.append({
                    "id": source.id,
                    "name": source.name,
                    "url": source.url,
                    "description": source.description,
                    "last_collected": source.last_scraped.replace(microsecond=0).isoformat() + 'Z' if source.last_scraped else None,
                    "proposal_count": proposal_count
                })
            
            return jsonify({"success": True, "sources": sources_data})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            close_session(session)
    
    @app.route("/api/data-sources/<int:source_id>/collect", methods=["POST"])
    def collect_from_source(source_id):
        """Collect data from a specific source"""
        session = get_session()
        
        try:
            # Get the data source
            data_source = session.query(DataSource).filter(DataSource.id == source_id).first()
            
            if not data_source:
                close_session(session)
                return jsonify({"success": False, "message": "Data source not found"}), 404
            
            # Use Celery to run the task asynchronously
            from src.tasks.scraper_tasks import force_collect_task
            task = force_collect_task.delay(source_id)
            
            close_session(session)
            
            return jsonify({
                "success": True,
                "message": f"Started collecting data from {data_source.name}",
                "task_id": task.id
            })
            
        except Exception as e:
            logger.error(f"Error collecting from source: {e}")
            close_session(session)
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route("/api/data-sources/collect-all", methods=["POST"])
    def collect_from_all_sources():
        """Collect data from all sources"""
        try:
            # Use Celery to run all scrapers asynchronously
            from src.tasks.scraper_tasks import run_all_scrapers_task
            task = run_all_scrapers_task.delay()
            
            return jsonify({
                "success": True,
                "message": "Started collecting data from all sources",
                "task_id": task.id
            })
            
        except Exception as e:
            logger.error(f"Error collecting from all sources: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route("/api/database-backups", methods=["GET"])
    def get_database_backups():
        """API endpoint to list database backups"""
        try:
            # Get the database directory
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_dir = os.path.join(project_root, 'data')
            
            # Get the list of backups
            backups = list_backups(db_dir)
            
            return jsonify({
                "status": "success",
                "backups": backups
            })
        except Exception as e:
            app.logger.error(f"Error listing database backups: {e}")
            return jsonify({
                "status": "error",
                "message": f"Error listing database backups: {str(e)}"
            }), 500
    
    @app.route("/api/database-backups/cleanup", methods=["POST"])
    def cleanup_database_backups():
        """API endpoint to clean up old database backups"""
        try:
            # Get the maximum number of backups to keep from the request
            data = request.get_json()
            max_backups = data.get("max_backups", 5)
            
            # Get the database directory
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_dir = os.path.join(project_root, 'data')
            
            # Clean up old backups
            cleanup_old_backups(db_dir, max_backups=max_backups)
            
            # Get the updated list of backups
            backups = list_backups(db_dir)
            
            return jsonify({
                "status": "success",
                "message": f"Successfully cleaned up database backups, keeping {max_backups} most recent",
                "backups": backups
            })
        except Exception as e:
            app.logger.error(f"Error cleaning up database backups: {e}")
            return jsonify({
                "status": "error",
                "message": f"Error cleaning up database backups: {str(e)}"
            }), 500
    
    @app.route("/api/reset-everything", methods=["POST"])
    def reset_everything():
        """API endpoint to delete all downloads and the database"""
        try:
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Close any existing database connections
            try:
                Session.remove()
                dispose_engine()
            except Exception as e:
                app.logger.warning(f"Error closing database connections: {e}")
            
            # Define paths to clean
            data_dir = os.path.join(project_root, 'data')
            downloads_dir = os.path.join(data_dir, 'downloads')
            db_path = os.path.join(data_dir, 'proposals.db')
            
            # Function to perform the reset in a background thread
            def perform_reset():
                try:
                    # Delete all downloads
                    if os.path.exists(downloads_dir):
                        app.logger.info(f"Deleting downloads directory: {downloads_dir}")
                        try:
                            # First try to delete all files in the directory
                            for root, dirs, files in os.walk(downloads_dir, topdown=False):
                                for file in files:
                                    try:
                                        file_path = os.path.join(root, file)
                                        app.logger.info(f"Deleting file: {file_path}")
                                        os.remove(file_path)
                                    except (PermissionError, OSError) as e:
                                        app.logger.warning(f"Could not delete file {file_path}: {e}")
                                
                                # Then try to delete empty directories
                                for dir in dirs:
                                    try:
                                        dir_path = os.path.join(root, dir)
                                        app.logger.info(f"Deleting directory: {dir_path}")
                                        os.rmdir(dir_path)
                                    except (PermissionError, OSError) as e:
                                        app.logger.warning(f"Could not delete directory {dir_path}: {e}")
                            
                            # Finally try to delete the main directory
                            try:
                                shutil.rmtree(downloads_dir)
                            except (PermissionError, OSError) as e:
                                app.logger.warning(f"Could not completely delete downloads directory: {e}")
                                # If we can't delete it, try to recreate it
                                if not os.path.exists(downloads_dir):
                                    os.makedirs(downloads_dir, exist_ok=True)
                        except Exception as e:
                            app.logger.warning(f"Error while deleting downloads directory: {e}")
                            # If we can't delete it, at least try to create it if it doesn't exist
                            if not os.path.exists(downloads_dir):
                                os.makedirs(downloads_dir, exist_ok=True)
                    else:
                        # Create the downloads directory if it doesn't exist
                        os.makedirs(downloads_dir, exist_ok=True)
                    
                    # Delete all database backups
                    backup_files = [f for f in os.listdir(data_dir) if f.startswith('proposals_backup_') and f.endswith('.db')]
                    for backup_file in backup_files:
                        backup_path = os.path.join(data_dir, backup_file)
                        app.logger.info(f"Deleting database backup: {backup_path}")
                        try:
                            os.remove(backup_path)
                        except (PermissionError, OSError) as e:
                            app.logger.warning(f"Could not delete backup file {backup_path}: {e}")
                    
                    # Delete the database
                    if os.path.exists(db_path):
                        app.logger.info(f"Deleting database: {db_path}")
                        try:
                            os.remove(db_path)
                        except (PermissionError, OSError) as e:
                            app.logger.warning(f"Could not delete database file {db_path}: {e}")
                    
                    # Initialize a new database
                    app.logger.info("Initializing new database")
                    init_database()
                    
                    # Reconnect to the database
                    from src.database.db import reconnect
                    reconnect()
                    
                    app.logger.info("Reset completed successfully")
                except Exception as e:
                    error_msg = f"Error during reset: {str(e)}"
                    app.logger.error(error_msg)
                    import traceback
                    app.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Start the reset in a background thread
            thread = threading.Thread(target=perform_reset)
            thread.daemon = True
            thread.start()
            
            return jsonify({
                "status": "success",
                "message": "Reset initiated. All downloads and database will be deleted and a new database will be created."
            })
        except Exception as e:
            app.logger.error(f"Error initiating reset: {e}")
            return jsonify({
                "status": "error",
                "message": f"Error initiating reset: {str(e)}"
            }), 500
    
    @app.route("/api/scraper-health")
    def get_scraper_health():
        """Get the health status of all scrapers"""
        session = get_session()
        try:
            # Join ScraperStatus with DataSource to get names
            results = session.query(
                DataSource.id,
                DataSource.name,
                ScraperStatus.status,
                ScraperStatus.last_checked,
                ScraperStatus.error_message,
                ScraperStatus.response_time
            ).outerjoin(
                ScraperStatus, DataSource.id == ScraperStatus.source_id
            ).all()
            
            # Format the results
            status_data = []
            for result in results:
                status_data.append({
                    "source_id": result[0],
                    "source_name": result[1],
                    "status": result[2] if result[2] else "unknown",
                    "last_checked": result[3].isoformat() if result[3] else None,
                    "error_message": result[4],
                    "response_time": result[5]
                })
            
            return jsonify({"success": True, "status": status_data})
        except Exception as e:
            logger.error(f"Error getting scraper health: {e}")
            return jsonify({"success": False, "error": str(e)})
        finally:
            close_session(session)

    @app.route("/api/scraper-health/check", methods=["POST"])
    def run_health_checks():
        """Run health checks on all scrapers"""
        try:
            # Use Celery to run the health checks asynchronously
            from src.tasks.health_check_tasks import check_all_scrapers_task
            task = check_all_scrapers_task.delay()
            
            return jsonify({
                "success": True,
                "message": "Health checks initiated",
                "task_id": task.id
            })
        except Exception as e:
            logger.error(f"Error initiating health checks: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @app.route("/api/scraper-health/<int:source_id>", methods=["POST"])
    def run_single_health_check(source_id):
        """Run a health check for a specific scraper"""
        session = get_session()
        try:
            # Get the data source
            data_source = session.query(DataSource).filter_by(id=source_id).first()
            if not data_source:
                close_session(session)
                return jsonify({"success": False, "error": "Data source not found"})
            
            # Use Celery to run the appropriate health check asynchronously
            if data_source.name == "Acquisition Gateway Forecast":
                from src.tasks.health_check_tasks import check_acquisition_gateway_task
                task = check_acquisition_gateway_task.delay()
            elif data_source.name == "SSA Contract Forecast":
                from src.tasks.health_check_tasks import check_ssa_contract_forecast_task
                task = check_ssa_contract_forecast_task.delay()
            else:
                close_session(session)
                return jsonify({
                    "success": False, 
                    "error": f"No health check function for {data_source.name}"
                })
            
            close_session(session)
            
            return jsonify({
                "success": True, 
                "message": f"Health check started for {data_source.name}",
                "task_id": task.id
            })
        except Exception as e:
            logger.error(f"Error starting health check: {e}")
            close_session(session)
            return jsonify({"success": False, "error": str(e)})
    
    return app 