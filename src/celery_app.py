"""
Celery application configuration for background task processing.

This module sets up the Celery application for handling background tasks such as
web scraping and health checks. It configures the Celery worker, task scheduling,
and connects to Redis for message brokering.
"""

import os
from celery import Celery
from celery.signals import task_failure, task_retry, task_success, worker_ready
from dotenv import load_dotenv
from src.config import active_config
from src.utils.logging import get_component_logger

# Load environment variables
load_dotenv()

# Configure logging using the centralized utility
logger = get_component_logger('celery')

# Get Redis URL from environment or use default from config
redis_url = active_config.REDIS_URL

# Define task modules
TASK_MODULES = [
    'src.background_tasks.scraper_tasks',
    'src.background_tasks.health_check_tasks'
]

# Create Celery app
celery_app = Celery(
    'jps_prospect_aggregate',
    broker=redis_url,
    backend=redis_url,
    include=TASK_MODULES
)

# Celery configuration (without beat schedule for now)
CELERY_CONFIG = {
    # Task settings
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    
    # Worker settings
    'worker_prefetch_multiplier': int(os.getenv("WORKER_PREFETCH_MULTIPLIER", 1)),  # Fetch one task at a time
    'worker_max_tasks_per_child': int(os.getenv("WORKER_MAX_TASKS_PER_CHILD", 100)),  # Restart worker after 100 tasks to prevent memory leaks
    
    # Result settings
    'result_expires': int(os.getenv("RESULT_EXPIRES", 3600)),  # Results expire after 1 hour
    
    # Beat settings (for scheduled tasks)
    'beat_schedule_filename': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp', 'celerybeat-schedule'),
    
    # Task retry settings
    'task_acks_late': True,  # Tasks are acknowledged after the task is executed
    'task_reject_on_worker_lost': True,  # Reject tasks when worker connection is lost
    'task_default_retry_delay': 60,  # Default retry delay in seconds
    'task_max_retries': 3,  # Maximum number of retries
    
    # Task time limits
    'task_time_limit': 3600,  # Hard time limit in seconds (1 hour)
    'task_soft_time_limit': 3000,  # Soft time limit in seconds (50 minutes)
}

# Apply configuration
celery_app.conf.update(CELERY_CONFIG)

@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    logger.info(f'Request: {self.request!r}')
    return "Celery is working!"

# Task signal handlers
@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **_):
    """Log task failures."""
    logger.error(f"Task {sender.name}[{task_id}] failed: {exception}")
    logger.error(f"Task args: {args}, kwargs: {kwargs}")
    if einfo:
        logger.error(f"Error info: {einfo}")

@task_retry.connect
def handle_task_retry(sender=None, request=None, reason=None, einfo=None, **_):
    """Log task retries."""
    logger.warning(f"Task {sender.name}[{request.id}] is being retried: {reason}")
    if einfo:
        logger.warning(f"Error info: {einfo}")

@task_success.connect
def handle_task_success(sender=None, result=None, **_):
    """Log task successes."""
    logger.info(f"Task {sender.name} completed successfully")

@worker_ready.connect
def handle_worker_ready(**_):
    """Log when a worker is ready."""
    logger.info("Celery worker is ready")

# Error handling for Celery tasks
@celery_app.on_after_configure.connect
def setup_error_handlers(sender, **kwargs):
    """Set up error handlers for Celery tasks."""
    logger.info("Setting up Celery error handlers")

@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    """Set up periodic tasks using the task registry and dynamic beat schedule."""
    logger.info("Setting up periodic tasks")
    
    # Import the task registry and schedule generator
    from src.background_tasks.registry import task_registry
    from src.background_tasks.schedule import generate_beat_schedule
    
    # Generate the beat schedule
    beat_schedule = generate_beat_schedule(task_registry)
    
    # Update the Celery configuration with the beat schedule
    sender.conf.beat_schedule = beat_schedule
    
    # Log the registered periodic tasks
    for task_name in sender.conf.beat_schedule.keys():
        logger.info(f"Registered periodic task: {task_name}")

if __name__ == '__main__':
    logger.info("Starting Celery worker")
    celery_app.start() 