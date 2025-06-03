from flask import Blueprint, jsonify
from sqlalchemy import func, desc
from app.models import db, Prospect, DataSource, ScraperStatus # Added ScraperStatus
from app.utils.logger import logger
import datetime

main_bp = Blueprint('main', __name__)

# Set up logging using the centralized utility
logger = logger.bind(name="api.main")

@main_bp.route('/', methods=['GET'])
def api_info():
    """API information endpoint."""
    return jsonify({
        'name': 'JPS Prospect Aggregate API',
        'version': '1.0.0',
        'description': 'API for managing government procurement prospects',
        'endpoints': {
            '/api/': 'This endpoint - API information',
            '/api/health': 'Health check endpoint',
            '/api/dashboard': 'Dashboard summary data',
            '/api/prospects': 'Prospects data with pagination'
        },
        'status': 'operational'
    })

@main_bp.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint."""
    try:
        session = db.session
        # Simple database query to check connection
        session.query(DataSource).first()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        # No rollback needed for a read operation that failed
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'database': 'disconnected', # More specific status
            'error': str(e)
        }), 500


@main_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Get dashboard summary information."""
    session = db.session
    try:
        # Get total number of prospects
        total_prospects = session.query(func.count(Prospect.id)).scalar()
        
        # Get newest data source update (last_scraped from DataSource)
        latest_successful_scrape = session.query(func.max(DataSource.last_scraped)).scalar()
        
        # Get top agencies by prospect count
        top_agencies = session.query(
            Prospect.agency,
            func.count(Prospect.id).label('prospect_count')
        ).group_by(Prospect.agency).order_by(desc('prospect_count')).limit(5).all()
        
        # Get upcoming prospects (using release_date)
        today = datetime.date.today() # Use datetime.date.today() for date comparison
        upcoming_prospects_data = session.query(Prospect).filter(
            Prospect.release_date >= today
        ).order_by(Prospect.release_date).limit(5).all()
        
        # Get recent scraper activity (last 5 completed or failed)
        recent_scraper_activity = session.query(DataSource.name, ScraperStatus.status, ScraperStatus.last_checked, ScraperStatus.details)\
            .join(ScraperStatus, DataSource.id == ScraperStatus.source_id)\
            .order_by(ScraperStatus.last_checked.desc())\
            .limit(5).all()

        return jsonify({
            "status": "success",
            "data": {
                "total_proposals": total_prospects,
                "latest_successful_scrape": latest_successful_scrape.isoformat() if latest_successful_scrape else None,
                "top_agencies": [{"agency": agency, "count": count} for agency, count in top_agencies],
                "upcoming_proposals": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "agency": p.agency,
                        "proposal_date": p.release_date.isoformat() if p.release_date else None
                    } for p in upcoming_prospects_data
                ],
                "recent_scraper_activity": [
                    {
                        "data_source_name": name,
                        "status": status,
                        "last_checked": last_checked.isoformat() if last_checked else None,
                        "details": details
                    } for name, status, last_checked, details in recent_scraper_activity
                ]
            }
        })
    except Exception as e:
        logger.error(f"Error in get_dashboard: {str(e)}", exc_info=True)
        # db.session.rollback() # Removed
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500

@main_bp.route('/database/clear', methods=['POST'])
def clear_database():
    """Clear all data from the database."""
    try:
        logger.info("Database clear operation initiated")
        
        # Delete all prospects first (due to foreign key constraints)
        prospect_count = db.session.query(func.count(Prospect.id)).scalar()
        db.session.query(Prospect).delete()
        
        # Reset the auto-increment counters if using SQLite
        try:
            db.session.execute('DELETE FROM sqlite_sequence WHERE name="prospects"')
            db.session.execute('DELETE FROM sqlite_sequence WHERE name="scraper_status"')
        except Exception:
            # Not SQLite or sequence doesn't exist, ignore
            pass
        
        # Clear scraper status records
        from app.models import ScraperStatus
        status_count = db.session.query(func.count(ScraperStatus.id)).scalar()
        db.session.query(ScraperStatus).delete()
        
        # Reset last_scraped on data sources
        data_sources = db.session.query(DataSource).all()
        for ds in data_sources:
            ds.last_scraped = None
        
        db.session.commit()
        
        logger.info(f"Database cleared successfully. Removed {prospect_count} prospects and {status_count} status records")
        
        return jsonify({
            'status': 'success',
            'message': f'Database cleared successfully. Removed {prospect_count} prospects and {status_count} status records.',
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error clearing database: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear database: {str(e)}'
        }), 500

@main_bp.route('/database/status', methods=['GET'])
def database_status():
    """Get database status and statistics."""
    try:
        # Get counts for all main tables
        prospect_count = db.session.query(func.count(Prospect.id)).scalar()
        data_source_count = db.session.query(func.count(DataSource.id)).scalar()
        
        # Count prospects with valid source_id vs total
        prospects_with_source = db.session.query(func.count(Prospect.id)).filter(Prospect.source_id.isnot(None)).scalar()
        prospects_without_source = prospect_count - prospects_with_source
        
        from app.models import ScraperStatus
        status_count = db.session.query(func.count(ScraperStatus.id)).scalar()
        
        # Get database file size if using SQLite
        db_size = None
        try:
            import os
            from flask import current_app
            db_path = current_app.config.get('SQLALCHEMY_DATABASE_URI')
            if db_path and db_path.startswith('sqlite:///'):
                db_file = db_path.replace('sqlite:///', '')
                if os.path.exists(db_file):
                    db_size = os.path.getsize(db_file)
        except Exception:
            pass
        
        return jsonify({
            'status': 'success',
            'data': {
                'prospect_count': prospect_count,
                'prospects_with_source': prospects_with_source,
                'prospects_without_source': prospects_without_source,
                'data_source_count': data_source_count,
                'status_record_count': status_count,
                'database_size_bytes': db_size,
                'timestamp': datetime.datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting database status: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get database status: {str(e)}'
        }), 500

# Add main/general routes here 