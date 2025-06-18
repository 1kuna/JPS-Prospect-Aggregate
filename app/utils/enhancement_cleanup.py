"""
Cleanup utility for stuck enhancement requests.

This module provides functions to clean up enhancement statuses that may be
stuck due to server restarts or unexpected shutdowns.
"""

from datetime import datetime, timedelta
from app.database import db
from app.database.models import Prospect
from app.utils.logger import logger

def cleanup_stuck_enhancements(max_age_hours=1):
    """
    Reset enhancement statuses that have been stuck for too long.
    
    Args:
        max_age_hours (int): Maximum hours an enhancement can be 'in_progress' 
                           before being considered stuck. Default is 1 hour.
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Find prospects that are stuck in enhancement
        stuck_prospects = db.session.query(Prospect).filter(
            Prospect.enhancement_status == 'in_progress',
            Prospect.enhancement_started_at < cutoff_time
        ).all()
        
        if not stuck_prospects:
            logger.info("No stuck enhancement requests found")
            return 0
            
        count = len(stuck_prospects)
        logger.info(f"Found {count} stuck enhancement requests, cleaning up...")
        
        # Reset their status to idle
        for prospect in stuck_prospects:
            logger.info(f"Resetting enhancement status for prospect {prospect.id}: {prospect.title[:50]}...")
            prospect.enhancement_status = 'idle'
            prospect.enhancement_started_at = None
            prospect.enhancement_user_id = None
            
        db.session.commit()
        logger.info(f"Successfully cleaned up {count} stuck enhancement requests")
        return count
        
    except Exception as e:
        logger.error(f"Error cleaning up stuck enhancements: {e}")
        db.session.rollback()
        raise

def cleanup_all_in_progress_enhancements():
    """
    Reset all prospects that are currently marked as 'in_progress' to 'idle'.
    
    This is useful when the server restarts and we want to reset all
    enhancement statuses since in-memory processing state is lost.
    """
    try:
        in_progress_prospects = db.session.query(Prospect).filter(
            Prospect.enhancement_status == 'in_progress'
        ).all()
        
        if not in_progress_prospects:
            logger.info("No in-progress enhancement requests found")
            return 0
            
        count = len(in_progress_prospects)
        logger.info(f"Found {count} in-progress enhancement requests, resetting to idle...")
        
        for prospect in in_progress_prospects:
            logger.info(f"Resetting prospect {prospect.id}: {prospect.title[:50] if prospect.title else 'No title'}...")
            prospect.enhancement_status = 'idle'
            prospect.enhancement_started_at = None
            prospect.enhancement_user_id = None
            
        db.session.commit()
        logger.info(f"Successfully reset {count} enhancement statuses to idle")
        return count
        
    except Exception as e:
        logger.error(f"Error resetting enhancement statuses: {e}")
        db.session.rollback()
        raise

def get_enhancement_statistics():
    """
    Get statistics about current enhancement statuses.
    
    Returns:
        dict: Statistics about enhancement statuses
    """
    try:
        stats = {}
        
        # Count by status
        for status in ['idle', 'in_progress', 'failed']:
            count = db.session.query(Prospect).filter(
                Prospect.enhancement_status == status
            ).count()
            stats[status] = count
            
        # Count long-running enhancements (over 1 hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        long_running = db.session.query(Prospect).filter(
            Prospect.enhancement_status == 'in_progress',
            Prospect.enhancement_started_at < cutoff_time
        ).count()
        stats['long_running'] = long_running
        
        # Total prospects
        stats['total'] = db.session.query(Prospect).count()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting enhancement statistics: {e}")
        return {}