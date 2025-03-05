import logging
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Set up logging
logger = logging.getLogger(__name__)

def schedule_health_checks(scheduler):
    """Schedule regular health checks for all scrapers"""
    from src.scrapers.health_check import check_all_scrapers
    
    # Run health checks every 10 minutes
    @scheduler.scheduled_job('interval', minutes=10, id='health_checks')
    def run_health_checks():
        logger.info("Running scheduled health checks")
        try:
            results = check_all_scrapers()
            logger.info(f"Health check results: {results}")
        except Exception as e:
            logger.error(f"Error running scheduled health checks: {e}")

def setup_scheduler():
    """Set up and start the scheduler"""
    scheduler = BackgroundScheduler()
    
    # Schedule all tasks
    # Add your existing scheduled tasks here
    
    # Schedule health checks
    schedule_health_checks(scheduler)
    
    # Start the scheduler
    scheduler.start()
    
    return scheduler 