import os
import sys
import threading
import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from sqlalchemy import func
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.db import get_session, close_session, engine, Session, dispose_engine
from src.database.models import Proposal, DataSource
from src.scrapers.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from src.scrapers.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper
from src.database.init_db import init_database

# Import the rebuild_database function
from rebuild_db import rebuild_database

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
        """API endpoint to get data sources"""
        session = get_session()
        
        try:
            sources = session.query(DataSource).all()
            
            result = []
            for source in sources:
                result.append({
                    "id": source.id,
                    "name": source.name,
                    "url": source.url,
                    "description": source.description
                })
            
            return jsonify(result)
        
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
            
            return jsonify({
                "agencies": agencies,
                "statuses": statuses
            })
        
        finally:
            close_session(session)
    
    @app.route("/api/refresh", methods=["POST"])
    def refresh_data():
        """API endpoint to trigger data refresh"""
        # Get the current timestamp before refresh
        current_time = datetime.datetime.utcnow()
        
        # Run the scraper in a background thread
        thread = threading.Thread(target=run_acquisition_gateway_scraper)
        thread.daemon = True
        thread.start()
        
        # Update all data sources with the current timestamp to prevent false update notifications
        session = get_session()
        try:
            # Update all data sources with the current timestamp
            session.query(DataSource).update({"last_scraped": current_time})
            session.commit()
        except Exception as e:
            app.logger.error(f"Error updating data source timestamps: {e}")
            session.rollback()
        finally:
            close_session(session)
        
        return jsonify({
            "status": "success", 
            "message": "Data refresh initiated",
            "timestamp": current_time.isoformat()
        })
    
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
        
        # Run the database rebuild in a background thread
        def rebuild_and_reconnect():
            try:
                # Rebuild the database
                rebuild_database()
                
                # Wait a moment for the rebuild to complete
                import time
                time.sleep(2)
                
                # Try to reconnect to the database
                from src.database.db import reconnect
                reconnect()
            except Exception as e:
                app.logger.error(f"Error during database rebuild: {e}")
        
        thread = threading.Thread(target=rebuild_and_reconnect)
        thread.daemon = True
        thread.start()
        
        # Return success response
        return jsonify({
            "status": "success", 
            "message": "Database rebuild initiated. The application may need to be restarted to use the new database."
        })
    
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
    def initialize_db():
        """API endpoint to initialize the database"""
        # Run the database initialization in a background thread
        thread = threading.Thread(target=init_database)
        thread.daemon = True
        thread.start()
        
        return jsonify({"status": "success", "message": "Database initialization initiated"})
    
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
            
            # Start the scraper in a separate thread
            def run_scraper():
                try:
                    if data_source.name == "Acquisition Gateway Forecast":
                        run_acquisition_gateway_scraper(force=True)
                    elif data_source.name == "SSA Contract Forecast":
                        run_ssa_contract_forecast_scraper(force=True)
                    else:
                        logger.error(f"Unknown data source: {data_source.name}")
                except Exception as e:
                    logger.error(f"Error running scraper: {e}")
            
            thread = threading.Thread(target=run_scraper)
            thread.daemon = True
            thread.start()
            
            close_session(session)
            
            return jsonify({
                "success": True,
                "message": f"Started collecting data from {data_source.name}"
            })
            
        except Exception as e:
            logger.error(f"Error collecting from source: {e}")
            close_session(session)
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route("/api/data-sources/collect-all", methods=["POST"])
    def collect_from_all_sources():
        """Collect data from all sources"""
        try:
            # Start the scrapers in separate threads
            def run_scrapers():
                try:
                    run_acquisition_gateway_scraper(force=True)
                    run_ssa_contract_forecast_scraper(force=True)
                except Exception as e:
                    logger.error(f"Error running scrapers: {e}")
            
            thread = threading.Thread(target=run_scrapers)
            thread.daemon = True
            thread.start()
            
            return jsonify({
                "success": True,
                "message": "Started collecting data from all sources"
            })
            
        except Exception as e:
            logger.error(f"Error collecting from all sources: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    return app 