"""
Celery application configuration for background task processing.

This module sets up the Celery application for handling background tasks such as
web scraping and health checks. It configures the Celery worker, task scheduling,
and connects to Redis for message brokering.
"""

import os
import logging
from celery import Celery
from dotenv import load_dotenv
from src.config import active_config

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Get Redis URL from environment or use default from config
redis_url = active_config.REDIS_URL

# Create Celery app
celery_app = Celery(
    'jps_prospect_aggregate',
    broker=redis_url,
    backend=redis_url,
    include=[
        'src.tasks.scraper_tasks',
        'src.tasks.health_check_tasks'
    ]
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=int(os.getenv("WORKER_PREFETCH_MULTIPLIER", 1)),  # Fetch one task at a time
    worker_max_tasks_per_child=int(os.getenv("WORKER_MAX_TASKS_PER_CHILD", 100)),  # Restart worker after 100 tasks to prevent memory leaks
    
    # Result settings
    result_expires=int(os.getenv("RESULT_EXPIRES", 3600)),  # Results expire after 1 hour
    
    # Beat settings (for scheduled tasks)
    beat_schedule_filename=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp', 'celerybeat-schedule'),
    
    beat_schedule={
        'run-acquisition-gateway-scraper': {
            'task': 'src.tasks.scraper_tasks.run_acquisition_gateway_scraper_task',
            'schedule': active_config.SCRAPE_INTERVAL_HOURS * 3600,  # Convert hours to seconds
            'args': (),
            'options': {'expires': 3600}  # Task expires if not executed within 1 hour
        },
        'run-ssa-contract-forecast-scraper': {
            'task': 'src.tasks.scraper_tasks.run_ssa_contract_forecast_scraper_task',
            'schedule': active_config.SCRAPE_INTERVAL_HOURS * 3600,  # Convert hours to seconds
            'args': (),
            'options': {'expires': 3600}  # Task expires if not executed within 1 hour
        },
        'check-all-scrapers': {
            'task': 'src.tasks.health_check_tasks.check_all_scrapers_task',
            'schedule': active_config.HEALTH_CHECK_INTERVAL_MINUTES * 60,  # Convert minutes to seconds
            'args': (),
            'options': {'expires': 600}  # Task expires if not executed within 10 minutes
        }
    }
)

@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    logger.info(f'Request: {self.request!r}')
    return "Celery is working!"

# Error handling for Celery tasks
@celery_app.on_after_configure.connect
def setup_error_handlers(sender, **kwargs):
    """Set up error handlers for Celery tasks."""
    logger.info("Setting up Celery error handlers")

@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    """Log that periodic tasks have been set up."""
    logger.info("Periodic tasks have been set up")
    for task_name in sender.conf.beat_schedule.keys():
        logger.info(f"Registered periodic task: {task_name}")

if __name__ == '__main__':
    logger.info("Starting Celery worker")
    celery_app.start() 