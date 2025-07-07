"""
Admin API endpoints for system administration.
"""

from flask import Blueprint, request, jsonify, session
from sqlalchemy import desc, func
from app.database import db
from app.database.models import Settings, GoNoGoDecision, Prospect
from app.database.user_models import User
from app.utils.logger import logger
from app.utils.user_utils import get_users_by_ids, get_user_data_dict, promote_user_to_admin, demote_admin_to_user
from app.api.auth import admin_required
from app.utils.enhancement_cleanup import (
    cleanup_stuck_enhancements, 
    cleanup_all_in_progress_enhancements,
    get_enhancement_statistics
)
import datetime

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


# === ADMIN-ONLY DECISION MANAGEMENT ENDPOINTS ===

@admin_bp.route('/decisions/all', methods=['GET'])
@admin_required
def get_all_decisions():
    """Get all decisions from all users with pagination and filtering."""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # Get filter parameters
        decision_filter = request.args.get('decision')  # 'go', 'no-go', or None for all
        user_id_filter = request.args.get('user_id', type=int)
        
        # Build query
        query = db.session.query(GoNoGoDecision).join(Prospect, GoNoGoDecision.prospect_id == Prospect.id)
        
        if decision_filter and decision_filter in ['go', 'no-go']:
            query = query.filter(GoNoGoDecision.decision == decision_filter)
        
        if user_id_filter:
            query = query.filter(GoNoGoDecision.user_id == user_id_filter)
        
        query = query.order_by(desc(GoNoGoDecision.created_at))
        
        # Get total count and paginated results
        total = query.count()
        decisions = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Get user data for all decisions
        user_ids = list(set([d.user_id for d in decisions]))
        users_data = get_users_by_ids(user_ids)
        
        # Build response data
        decision_data = []
        for decision in decisions:
            user_data = get_user_data_dict(users_data.get(decision.user_id))
            decision_dict = decision.to_dict(include_user=True, user_data=user_data)
            # Add prospect title for admin view
            decision_dict['prospect_title'] = decision.prospect.title if decision.prospect else None
            decision_data.append(decision_dict)
        
        return jsonify({
            'status': 'success',
            'data': {
                'decisions': decision_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                },
                'filters': {
                    'decision': decision_filter,
                    'user_id': user_id_filter
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting all decisions: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to get decisions'
        }), 500


@admin_bp.route('/decisions/stats', methods=['GET'])
@admin_required
def get_admin_decision_stats():
    """Get system-wide decision statistics for admin view."""
    try:
        # Overall stats
        total_decisions = db.session.query(func.count(GoNoGoDecision.id)).scalar()
        total_go = db.session.query(func.count(GoNoGoDecision.id)).filter(GoNoGoDecision.decision == 'go').scalar()
        total_nogo = db.session.query(func.count(GoNoGoDecision.id)).filter(GoNoGoDecision.decision == 'no-go').scalar()
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
        recent_decisions = db.session.query(func.count(GoNoGoDecision.id)).filter(
            GoNoGoDecision.created_at >= thirty_days_ago
        ).scalar()
        
        # User stats
        user_stats = db.session.query(
            GoNoGoDecision.user_id,
            func.count(GoNoGoDecision.id).label('total'),
            func.sum(func.case([(GoNoGoDecision.decision == 'go', 1)], else_=0)).label('go_count'),
            func.sum(func.case([(GoNoGoDecision.decision == 'no-go', 1)], else_=0)).label('nogo_count')
        ).group_by(GoNoGoDecision.user_id).all()
        
        # Get user data for the stats
        user_ids = [stat.user_id for stat in user_stats]
        users_data = get_users_by_ids(user_ids)
        
        user_statistics = []
        for stat in user_stats:
            user = users_data.get(stat.user_id)
            user_statistics.append({
                'user_id': stat.user_id,
                'user_email': user.email if user else 'Unknown',
                'user_name': user.first_name if user else 'Unknown',
                'total_decisions': stat.total,
                'go_decisions': stat.go_count,
                'nogo_decisions': stat.nogo_count,
                'go_percentage': round((stat.go_count / stat.total) * 100, 1) if stat.total > 0 else 0
            })
        
        # Sort by total decisions descending
        user_statistics.sort(key=lambda x: x['total_decisions'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'data': {
                'overall': {
                    'total_decisions': total_decisions,
                    'go_decisions': total_go,
                    'nogo_decisions': total_nogo,
                    'recent_decisions_30d': recent_decisions,
                    'go_percentage': round((total_go / total_decisions) * 100, 1) if total_decisions > 0 else 0
                },
                'by_user': user_statistics
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting admin decision stats: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to get decision statistics'
        }), 500


@admin_bp.route('/decisions/export', methods=['GET'])
@admin_required
def export_all_decisions():
    """Export all decisions to CSV format for admin analysis."""
    try:
        # Get all decisions with prospect and user data
        decisions = db.session.query(GoNoGoDecision).join(
            Prospect, GoNoGoDecision.prospect_id == Prospect.id
        ).order_by(desc(GoNoGoDecision.created_at)).all()
        
        # Get user data
        user_ids = list(set([d.user_id for d in decisions]))
        users_data = get_users_by_ids(user_ids)
        
        # Build CSV data
        csv_data = []
        for decision in decisions:
            user = users_data.get(decision.user_id)
            csv_data.append({
                'decision_id': decision.id,
                'prospect_id': decision.prospect_id,
                'prospect_title': decision.prospect.title if decision.prospect else '',
                'prospect_agency': decision.prospect.agency if decision.prospect else '',
                'user_id': decision.user_id,
                'user_email': user.email if user else 'Unknown',
                'user_name': user.first_name if user else 'Unknown',
                'decision': decision.decision,
                'reason': decision.reason or '',
                'created_at': decision.created_at.isoformat() if decision.created_at else '',
                'updated_at': decision.updated_at.isoformat() if decision.updated_at else ''
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'decisions': csv_data,
                'total_count': len(csv_data),
                'export_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error exporting decisions: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to export decisions'
        }), 500


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users with their decision activity."""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # Get all users with pagination
        query = db.session.query(User).order_by(desc(User.created_at))
        total = query.count()
        users = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Get decision counts for each user
        user_ids = [user.id for user in users]
        decision_counts = db.session.query(
            GoNoGoDecision.user_id,
            func.count(GoNoGoDecision.id).label('total_decisions'),
            func.sum(func.case([(GoNoGoDecision.decision == 'go', 1)], else_=0)).label('go_count'),
            func.sum(func.case([(GoNoGoDecision.decision == 'no-go', 1)], else_=0)).label('nogo_count')
        ).filter(GoNoGoDecision.user_id.in_(user_ids)).group_by(GoNoGoDecision.user_id).all()
        
        # Create lookup dict for decision counts
        decision_lookup = {dc.user_id: dc for dc in decision_counts}
        
        # Build user data with decision stats
        user_data = []
        for user in users:
            user_dict = user.to_dict()
            decision_count = decision_lookup.get(user.id)
            if decision_count:
                user_dict['decision_stats'] = {
                    'total_decisions': decision_count.total_decisions,
                    'go_decisions': decision_count.go_count,
                    'nogo_decisions': decision_count.nogo_count
                }
            else:
                user_dict['decision_stats'] = {
                    'total_decisions': 0,
                    'go_decisions': 0,
                    'nogo_decisions': 0
                }
            user_data.append(user_dict)
        
        return jsonify({
            'status': 'success',
            'data': {
                'users': user_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting all users: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to get users'
        }), 500


@admin_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def update_user_role(user_id):
    """Update a user's role (promote/demote admin)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        new_role = data.get('role', '').strip().lower()
        if new_role not in ['user', 'admin']:
            return jsonify({
                'status': 'error',
                'message': 'Role must be either "user" or "admin"'
            }), 400
        
        # Don't allow users to demote themselves
        current_user_id = session.get('user_id')
        if current_user_id == user_id and new_role == 'user':
            return jsonify({
                'status': 'error',
                'message': 'You cannot demote yourself from admin'
            }), 400
        
        # Update the user role
        success = promote_user_to_admin(user_id) if new_role == 'admin' else demote_admin_to_user(user_id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        logger.info(f"User {user_id} role updated to {new_role} by admin {current_user_id}")
        
        return jsonify({
            'status': 'success',
            'message': f'User role updated to {new_role} successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating user role: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to update user role'
        }), 500