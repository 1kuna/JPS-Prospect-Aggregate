"""
Admin API endpoints for system administration.
"""

from flask import Blueprint, request, jsonify
from app.database import db
from app.database.models import Settings
from app.utils.logger import logger
from app.utils.enhancement_cleanup import (
    cleanup_stuck_enhancements, 
    cleanup_all_in_progress_enhancements,
    get_enhancement_statistics
)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/maintenance', methods=['GET', 'POST'])
def toggle_maintenance():
    """
    GET: Get current maintenance mode status
    POST: Toggle maintenance mode on/off
    
    POST Body:
    {
        "enabled": true/false
    }
    """
    try:
        if request.method == 'GET':
            # Get current maintenance status
            setting = db.session.query(Settings).filter_by(key='maintenance_mode').first()
            if setting:
                is_enabled = setting.value.lower() == 'true'
            else:
                is_enabled = False
                
            return jsonify({
                "maintenance_mode": is_enabled,
                "message": "Maintenance mode is currently " + ("enabled" if is_enabled else "disabled")
            })
            
        elif request.method == 'POST':
            # Toggle maintenance mode
            data = request.get_json() or {}
            enabled = data.get('enabled', None)
            
            if enabled is None:
                return jsonify({"error": "Missing 'enabled' parameter"}), 400
                
            if not isinstance(enabled, bool):
                return jsonify({"error": "'enabled' parameter must be true or false"}), 400
            
            # Get or create the maintenance_mode setting
            setting = db.session.query(Settings).filter_by(key='maintenance_mode').first()
            if setting:
                setting.value = 'true' if enabled else 'false'
            else:
                setting = Settings(
                    key='maintenance_mode',
                    value='true' if enabled else 'false',
                    description='Controls whether the site is in maintenance mode'
                )
                db.session.add(setting)
            
            db.session.commit()
            
            status_message = "enabled" if enabled else "disabled"
            logger.info(f"Maintenance mode {status_message} via admin API")
            
            return jsonify({
                "success": True,
                "maintenance_mode": enabled,
                "message": f"Maintenance mode has been {status_message}"
            })
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error managing maintenance mode: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route('/settings', methods=['GET'])
def get_all_settings():
    """Get all system settings."""
    try:
        settings = db.session.query(Settings).all()
        return jsonify({
            "settings": [setting.to_dict() for setting in settings]
        })
    except Exception as e:
        logger.error(f"Error fetching settings: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route('/health', methods=['GET'])
def admin_health():
    """Health check endpoint that works even in maintenance mode."""
    try:
        # Test database connection
        db.session.execute("SELECT 1")
        
        # Get maintenance status
        setting = db.session.query(Settings).filter_by(key='maintenance_mode').first()
        maintenance_enabled = setting.value.lower() == 'true' if setting else False
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "maintenance_mode": maintenance_enabled,
            "timestamp": db.func.now()
        })
    except Exception as e:
        logger.error(f"Admin health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@admin_bp.route('/enhancement-cleanup', methods=['POST'])
def cleanup_enhancements():
    """
    Clean up stuck enhancement requests.
    
    POST Body (optional):
    {
        "type": "stuck" | "all",  // Default: "stuck"
        "max_age_hours": 1        // Only for "stuck" type, default: 1
    }
    """
    try:
        data = request.get_json() or {}
        cleanup_type = data.get('type', 'stuck')
        max_age_hours = data.get('max_age_hours', 1)
        
        if cleanup_type not in ['stuck', 'all']:
            return jsonify({"error": "cleanup type must be 'stuck' or 'all'"}), 400
            
        if cleanup_type == 'all':
            count = cleanup_all_in_progress_enhancements()
            message = f"Reset {count} in-progress enhancement requests to idle"
        else:
            count = cleanup_stuck_enhancements(max_age_hours=max_age_hours)
            message = f"Cleaned up {count} stuck enhancement requests (older than {max_age_hours} hours)"
            
        logger.info(f"Enhancement cleanup completed: {message}")
        
        return jsonify({
            "success": True,
            "count": count,
            "message": message,
            "type": cleanup_type
        })
        
    except Exception as e:
        logger.error(f"Error during enhancement cleanup: {str(e)}")
        return jsonify({"error": f"Cleanup failed: {str(e)}"}), 500


@admin_bp.route('/enhancement-stats', methods=['GET'])
def enhancement_statistics():
    """Get statistics about current enhancement statuses."""
    try:
        stats = get_enhancement_statistics()
        return jsonify({
            "success": True,
            "statistics": stats
        })
    except Exception as e:
        logger.error(f"Error getting enhancement statistics: {str(e)}")
        return jsonify({"error": f"Failed to get statistics: {str(e)}"}), 500