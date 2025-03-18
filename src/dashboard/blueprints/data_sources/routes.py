"""Routes for the data sources blueprint."""

from flask import render_template, current_app, jsonify, request, redirect, url_for, send_from_directory
import threading
from . import data_sources
from src.database.db_session_manager import get_session, close_session, Session, dispose_engine, session_scope
from src.database.models import DataSource, ScraperStatus
from src.data_collectors.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from src.data_collectors.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper
from src.utils.db_utils import rebuild_database, cleanup_old_backups
from src.exceptions import ScraperError
from src.utils.imports import (
    os, datetime, traceback, glob, sqlite3
)
from src.utils.file_utils import find_valid_files, ensure_directories

@data_sources.route('/run-scraper/<int:source_id>', methods=['POST'])
def run_scraper(source_id):
    """API endpoint to manually run a scraper."""
    session = get_session()
    
    try:
        # Get the data source
        data_source = session.query(DataSource).filter(DataSource.id == source_id).first()
        
        if not data_source:
            return jsonify({
                "status": "error",
                "message": f"Data source with ID {source_id} not found"
            }), 404
        
        current_app.logger.info(f"Running scraper for {data_source.name}")
        
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
        if data_source.name == "Acquisition Gateway Forecast":
            try:
                # Import the check_url_accessibility function
                from src.data_collectors.acquisition_gateway import check_url_accessibility, ACQUISITION_GATEWAY_URL
                
                # Check if the URL is accessible
                if not check_url_accessibility(ACQUISITION_GATEWAY_URL):
                    return jsonify({
                        "status": "error",
                        "message": f"The URL {ACQUISITION_GATEWAY_URL} is not accessible. Please check your internet connection or if the website is down."
                    }), 500
                
                # Run the scraper in a separate thread to avoid blocking the response
                def run_scraper_thread():
                    try:
                        # Update the scraper status to "running"
                        with session_scope() as session:
                            scraper_status = session.query(ScraperStatus).filter(
                                ScraperStatus.data_source_id == data_source.id
                            ).first()
                            
                            if not scraper_status:
                                scraper_status = ScraperStatus(
                                    data_source_id=data_source.id,
                                    status="running",
                                    message="Scraper is running...",
                                    last_updated=datetime.datetime.utcnow()
                                )
                                session.add(scraper_status)
                            else:
                                scraper_status.status = "running"
                                scraper_status.message = "Scraper is running..."
                                scraper_status.last_updated = datetime.datetime.utcnow()
                            
                            session.commit()
                        
                        current_app.logger.info(f"Starting scraper for {data_source.name}")
                        
                        try:
                            # Run the scraper - this will now raise ScraperError on failure
                            run_acquisition_gateway_scraper(force=True)
                            
                            # If we get here, the scraper was successful
                            with session_scope() as session:
                                scraper_status = session.query(ScraperStatus).filter(
                                    ScraperStatus.data_source_id == data_source.id
                                ).first()
                                
                                if scraper_status:
                                    scraper_status.status = "success"
                                    scraper_status.message = "Scraper completed successfully"
                                    scraper_status.last_updated = datetime.datetime.utcnow()
                                    session.commit()
                            
                            current_app.logger.info(f"Scraper completed successfully")
                        except ScraperError as se:
                            # Handle specific scraper errors with detailed messages
                            error_msg = str(se)
                            current_app.logger.error(f"Scraper error: {error_msg}")
                            
                            with session_scope() as session:
                                scraper_status = session.query(ScraperStatus).filter(
                                    ScraperStatus.data_source_id == data_source.id
                                ).first()
                                
                                if scraper_status:
                                    scraper_status.status = "error"
                                    scraper_status.message = f"Error: {error_msg}"
                                    scraper_status.last_updated = datetime.datetime.utcnow()
                                    session.commit()
                    except Exception as e:
                        current_app.logger.error(f"Error in scraper thread: {str(e)}")
                        current_app.logger.error(traceback.format_exc())
                        
                        # Update the scraper status to "error"
                        with session_scope() as session:
                            scraper_status = session.query(ScraperStatus).filter(
                                ScraperStatus.data_source_id == data_source.id
                            ).first()
                            
                            if scraper_status:
                                scraper_status.status = "error"
                                scraper_status.message = f"Error: {str(e)}"
                                scraper_status.last_updated = datetime.datetime.utcnow()
                                session.commit()
                
                thread = threading.Thread(target=run_scraper_thread)
                thread.daemon = True
                thread.start()
                
                return jsonify({
                    "status": "success",
                    "message": f"Started pulling data from {data_source.name}. This may take a while..."
                })
            except Exception as e:
                current_app.logger.error(f"Error running Acquisition Gateway scraper: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                return jsonify({
                    "status": "error",
                    "message": f"Error running scraper: {str(e)}"
                }), 500
        elif data_source.name == "SSA Contract Forecast":
            try:
                # Import the check_url_accessibility function
                from src.data_collectors.ssa_contract_forecast import check_url_accessibility, SSA_CONTRACT_FORECAST_URL
                
                # Check if the URL is accessible
                if not check_url_accessibility(SSA_CONTRACT_FORECAST_URL):
                    return jsonify({
                        "status": "error",
                        "message": f"The URL {SSA_CONTRACT_FORECAST_URL} is not accessible. Please check your internet connection or if the website is down."
                    }), 500
                
                # Run the scraper in a separate thread to avoid blocking the response
                def run_scraper_thread():
                    try:
                        # Update the scraper status to "running"
                        with session_scope() as session:
                            scraper_status = session.query(ScraperStatus).filter(
                                ScraperStatus.data_source_id == data_source.id
                            ).first()
                            
                            if not scraper_status:
                                scraper_status = ScraperStatus(
                                    data_source_id=data_source.id,
                                    status="running",
                                    message="Scraper is running...",
                                    last_updated=datetime.datetime.utcnow()
                                )
                                session.add(scraper_status)
                            else:
                                scraper_status.status = "running"
                                scraper_status.message = "Scraper is running..."
                                scraper_status.last_updated = datetime.datetime.utcnow()
                            
                            session.commit()
                        
                        current_app.logger.info(f"Starting scraper for {data_source.name}")
                        
                        try:
                            # Run the scraper - this will now raise ScraperError on failure
                            run_ssa_contract_forecast_scraper(force=True)
                            
                            # If we get here, the scraper was successful
                            with session_scope() as session:
                                scraper_status = session.query(ScraperStatus).filter(
                                    ScraperStatus.data_source_id == data_source.id
                                ).first()
                                
                                if scraper_status:
                                    scraper_status.status = "success"
                                    scraper_status.message = "Scraper completed successfully"
                                    scraper_status.last_updated = datetime.datetime.utcnow()
                                    session.commit()
                            
                            current_app.logger.info(f"Scraper completed successfully")
                        except ScraperError as se:
                            # Handle specific scraper errors with detailed messages
                            error_msg = str(se)
                            current_app.logger.error(f"Scraper error: {error_msg}")
                            
                            with session_scope() as session:
                                scraper_status = session.query(ScraperStatus).filter(
                                    ScraperStatus.data_source_id == data_source.id
                                ).first()
                                
                                if scraper_status:
                                    scraper_status.status = "error"
                                    scraper_status.message = f"Error: {error_msg}"
                                    scraper_status.last_updated = datetime.datetime.utcnow()
                                    session.commit()
                    except Exception as e:
                        current_app.logger.error(f"Error in scraper thread: {str(e)}")
                        current_app.logger.error(traceback.format_exc())
                        
                        # Update the scraper status to "error"
                        with session_scope() as session:
                            scraper_status = session.query(ScraperStatus).filter(
                                ScraperStatus.data_source_id == data_source.id
                            ).first()
                            
                            if scraper_status:
                                scraper_status.status = "error"
                                scraper_status.message = f"Error: {str(e)}"
                                scraper_status.last_updated = datetime.datetime.utcnow()
                                session.commit()
                
                thread = threading.Thread(target=run_scraper_thread)
                thread.daemon = True
                thread.start()
                
                return jsonify({
                    "status": "success",
                    "message": f"Started pulling data from {data_source.name}. This may take a while..."
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
                "message": f"Unknown data source: {data_source.name}"
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error running scraper: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": f"Error running scraper: {str(e)}"
        }), 500
    finally:
        close_session(session)

@data_sources.route('/<int:source_id>/status', methods=['GET'])
def get_scraper_status(source_id):
    """API endpoint to get the status of a scraper."""
    session = get_session()
    
    try:
        # Get the data source
        data_source = session.query(DataSource).filter(DataSource.id == source_id).first()
        
        if not data_source:
            return jsonify({
                "status": "error",
                "message": f"Data source with ID {source_id} not found"
            }), 404
        
        # Get the scraper status
        scraper_status = session.query(ScraperStatus).filter(
            ScraperStatus.data_source_id == source_id
        ).first()
        
        if not scraper_status:
            return jsonify({
                "status": "unknown",
                "message": "No status information available for this scraper"
            })
        
        # Check if the scraper has been running for too long (more than 3 minutes)
        if scraper_status.status == "running" and scraper_status.last_updated:
            time_running = datetime.datetime.utcnow() - scraper_status.last_updated
            if time_running.total_seconds() > 180:  # 3 minutes (reduced from 5 minutes/300 seconds)
                # Update the status to error
                scraper_status.status = "error"
                scraper_status.message = f"Scraper timed out after running for {int(time_running.total_seconds() / 60)} minutes"
                scraper_status.last_updated = datetime.datetime.utcnow()
                session.commit()
                
                current_app.logger.warning(f"Scraper for data source {source_id} timed out after {int(time_running.total_seconds() / 60)} minutes")
        
        # Return the status
        return jsonify({
            "status": scraper_status.status,
            "message": scraper_status.message,
            "last_updated": scraper_status.last_updated.isoformat() if scraper_status.last_updated else None,
            "last_checked": scraper_status.last_checked.isoformat() if scraper_status.last_checked else None
        })
    except Exception as e:
        current_app.logger.error(f"Error getting scraper status: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error getting scraper status: {str(e)}"
        }), 500
    finally:
        close_session(session)

@data_sources.route('/rebuild-db', methods=['POST'])
def rebuild_db():
    """API endpoint to trigger database rebuild."""
    # Close any existing database connections
    try:
        # Close all existing connections
        Session.remove()
        dispose_engine()
    except Exception as e:
        current_app.logger.warning(f"Error closing database connections: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error closing database connections: {str(e)}"
        }), 500
    
    # Run the database rebuild in a background thread
    def rebuild_and_reconnect():
        try:
            # Rebuild the database
            current_app.logger.info("Starting database rebuild process")
            rebuild_database()
            
            # Wait a moment for the rebuild to complete
            import time
            time.sleep(2)
            
            # Try to reconnect to the database
            from src.database.db_session_manager import reconnect
            reconnect()
            current_app.logger.info("Database rebuild completed successfully")
        except Exception as e:
            error_msg = f"Error during database rebuild: {str(e)}"
            current_app.logger.error(error_msg)
            # Log the full traceback for debugging
            import traceback
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
    
    try:
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
            "message": f"Error starting rebuild thread: {str(e)}"
        }), 500

@data_sources.route('/database/backups', methods=['GET'])
def list_backups():
    """API endpoint to list all database backups."""
    try:
        # Get the database directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_dir = os.path.join(project_root, 'data')
        
        # Find all database backup files using find_valid_files
        backup_files = find_valid_files(db_dir, 'proposals_backup_*.db')
        
        # Sort files by modification time (newest first)
        backup_files = sorted(backup_files, key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Prepare the list of backups with details
        backups = []
        for backup in backup_files:
            size_bytes = os.path.getsize(backup)
            size_mb = size_bytes / (1024 * 1024)
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(backup))
            backups.append({
                'id': os.path.basename(backup).replace('proposals_backup_', '').replace('.db', ''),
                'file': os.path.basename(backup),
                'size': f"{size_mb:.2f} MB",
                'created_at': mod_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return jsonify({
            'status': 'success',
            'data': backups
        })
    except Exception as e:
        current_app.logger.error(f"Error listing backups: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@data_sources.route('/database/backups', methods=['POST'])
def create_backup():
    """API endpoint to create a database backup."""
    try:
        # Get the database directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_dir = os.path.join(project_root, 'data')
        db_path = os.path.join(db_dir, 'proposals.db')
        
        # Create a backup with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(db_dir, f'proposals_backup_{timestamp}.db')
        
        # Copy the database file
        import shutil
        shutil.copy2(db_path, backup_path)
        
        # Clean up old backups
        cleanup_old_backups(db_dir)
        
        return jsonify({
            'status': 'success',
            'message': 'Backup created successfully',
            'data': {
                'id': timestamp,
                'file': os.path.basename(backup_path)
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error creating backup: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@data_sources.route('/database/backups/<backup_id>/restore', methods=['POST'])
def restore_backup(backup_id):
    """API endpoint to restore a database from backup."""
    try:
        # Get the database directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_dir = os.path.join(project_root, 'data')
        db_path = os.path.join(db_dir, 'proposals.db')
        backup_path = os.path.join(db_dir, f'proposals_backup_{backup_id}.db')
        
        # Check if backup exists
        if not os.path.exists(backup_path):
            return jsonify({
                'status': 'error',
                'message': 'Backup file not found'
            }), 404
        
        # Close all existing database connections
        try:
            Session.remove()
            dispose_engine()
        except Exception as e:
            current_app.logger.warning(f"Error closing database connections: {e}")
        
        # Create a backup of the current database before restoring
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        current_backup_path = os.path.join(db_dir, f'proposals_backup_{timestamp}.db')
        import shutil
        shutil.copy2(db_path, current_backup_path)
        
        # Restore the backup
        shutil.copy2(backup_path, db_path)
        
        # Clean up old backups
        cleanup_old_backups(db_dir)
        
        return jsonify({
            'status': 'success',
            'message': 'Database restored successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Error restoring backup: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@data_sources.route('/database/initialize', methods=['POST'])
def initialize_db():
    """API endpoint to initialize the database."""
    try:
        # Close all existing database connections
        try:
            Session.remove()
            dispose_engine()
        except Exception as e:
            current_app.logger.warning(f"Error closing database connections: {e}")
        
        # Get the database path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_dir = os.path.join(project_root, 'data')
        db_path = os.path.join(db_dir, 'proposals.db')
        
        # Create a backup before initializing
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(db_dir, f'proposals_backup_{timestamp}.db')
        
        if os.path.exists(db_path):
            import shutil
            shutil.copy2(db_path, backup_path)
            cleanup_old_backups(db_dir)
        
        # Initialize the database with empty tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create data_sources table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_sources (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            url VARCHAR(255) NOT NULL,
            description TEXT,
            last_scraped TIMESTAMP
        )
        """)
        
        # Create proposals table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            external_id VARCHAR(100),
            title VARCHAR(255) NOT NULL,
            agency VARCHAR(100),
            office VARCHAR(100),
            description TEXT,
            naics_code VARCHAR(20),
            estimated_value FLOAT,
            release_date TIMESTAMP,
            response_date TIMESTAMP,
            contact_info TEXT,
            url VARCHAR(255),
            status VARCHAR(50),
            last_updated TIMESTAMP,
            imported_at TIMESTAMP,
            is_latest BOOLEAN,
            contract_type VARCHAR(100),
            set_aside VARCHAR(100),
            competition_type VARCHAR(100),
            solicitation_number VARCHAR(100),
            award_date TIMESTAMP,
            place_of_performance TEXT,
            incumbent VARCHAR(255),
            FOREIGN KEY (source_id) REFERENCES data_sources (id)
        )
        """)
        
        # Create proposal_history table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS proposal_history (
            id INTEGER PRIMARY KEY,
            proposal_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            external_id VARCHAR(100),
            title VARCHAR(255) NOT NULL,
            agency VARCHAR(100),
            office VARCHAR(100),
            description TEXT,
            naics_code VARCHAR(20),
            estimated_value FLOAT,
            release_date TIMESTAMP,
            response_date TIMESTAMP,
            contact_info TEXT,
            url VARCHAR(255),
            status VARCHAR(50),
            imported_at TIMESTAMP,
            contract_type VARCHAR(100),
            set_aside VARCHAR(100),
            competition_type VARCHAR(100),
            solicitation_number VARCHAR(100),
            award_date TIMESTAMP,
            place_of_performance TEXT,
            incumbent VARCHAR(255),
            FOREIGN KEY (proposal_id) REFERENCES proposals (id),
            FOREIGN KEY (source_id) REFERENCES data_sources (id)
        )
        """)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Database initialized successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Error initializing database: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@data_sources.route('/database/reset', methods=['POST'])
def reset_everything():
    """API endpoint to reset everything."""
    try:
        # Close all existing database connections
        try:
            Session.remove()
            dispose_engine()
        except Exception as e:
            current_app.logger.warning(f"Error closing database connections: {e}")
        
        # Get the database path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_dir = os.path.join(project_root, 'data')
        db_path = os.path.join(db_dir, 'proposals.db')
        
        # Create a backup before resetting
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(db_dir, f'proposals_backup_{timestamp}.db')
        
        if os.path.exists(db_path):
            import shutil
            shutil.copy2(db_path, backup_path)
            cleanup_old_backups(db_dir)
            os.remove(db_path)
        
        # Create a new empty database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create data_sources table
        cursor.execute("""
        CREATE TABLE data_sources (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            url VARCHAR(255) NOT NULL,
            description TEXT,
            last_scraped TIMESTAMP
        )
        """)
        
        # Create proposals table
        cursor.execute("""
        CREATE TABLE proposals (
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            external_id VARCHAR(100),
            title VARCHAR(255) NOT NULL,
            agency VARCHAR(100),
            office VARCHAR(100),
            description TEXT,
            naics_code VARCHAR(20),
            estimated_value FLOAT,
            release_date TIMESTAMP,
            response_date TIMESTAMP,
            contact_info TEXT,
            url VARCHAR(255),
            status VARCHAR(50),
            last_updated TIMESTAMP,
            imported_at TIMESTAMP,
            is_latest BOOLEAN,
            contract_type VARCHAR(100),
            set_aside VARCHAR(100),
            competition_type VARCHAR(100),
            solicitation_number VARCHAR(100),
            award_date TIMESTAMP,
            place_of_performance TEXT,
            incumbent VARCHAR(255),
            FOREIGN KEY (source_id) REFERENCES data_sources (id)
        )
        """)
        
        # Create proposal_history table
        cursor.execute("""
        CREATE TABLE proposal_history (
            id INTEGER PRIMARY KEY,
            proposal_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            external_id VARCHAR(100),
            title VARCHAR(255) NOT NULL,
            agency VARCHAR(100),
            office VARCHAR(100),
            description TEXT,
            naics_code VARCHAR(20),
            estimated_value FLOAT,
            release_date TIMESTAMP,
            response_date TIMESTAMP,
            contact_info TEXT,
            url VARCHAR(255),
            status VARCHAR(50),
            imported_at TIMESTAMP,
            contract_type VARCHAR(100),
            set_aside VARCHAR(100),
            competition_type VARCHAR(100),
            solicitation_number VARCHAR(100),
            award_date TIMESTAMP,
            place_of_performance TEXT,
            incumbent VARCHAR(255),
            FOREIGN KEY (proposal_id) REFERENCES proposals (id),
            FOREIGN KEY (source_id) REFERENCES data_sources (id)
        )
        """)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Database reset successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Error resetting database: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 