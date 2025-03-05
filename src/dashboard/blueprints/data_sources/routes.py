"""Routes for the data sources blueprint."""

from flask import render_template, current_app, jsonify, request
import threading
from . import data_sources
from src.database.db import get_session, close_session, Session, dispose_engine
from src.database.models import DataSource, ScraperStatus
from src.scrapers.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from src.scrapers.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper
from scripts.rebuild_db import rebuild_database

@data_sources.route('/')
def index():
    """Render the data sources page."""
    return render_template('data_sources/data_sources.html')

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
        
        # Run the appropriate scraper based on the data source name
        if data_source.name == "Acquisition Gateway Forecast":
            success = run_acquisition_gateway_scraper(force=True)
        elif data_source.name == "SSA Contract Forecast":
            success = run_ssa_contract_forecast_scraper(force=True)
        else:
            return jsonify({
                "status": "error",
                "message": f"Unknown data source: {data_source.name}"
            }), 400
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Scraper for {data_source.name} ran successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Scraper for {data_source.name} failed"
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error running scraper: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
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
            from src.database.db import reconnect
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