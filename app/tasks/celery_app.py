"""
Simplified Celery application configuration.
"""

import os
from celery import Celery
from celery.signals import task_failure, task_success, worker_ready
from dotenv import load_dotenv
from src.utils.logger import logger

# Load environment variables
load_dotenv()

# Get Redis URL from environment or use default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Define task modules to include
TASK_MODULES = [
    'src.tasks.scrapers',
    'src.tasks.health',
    'src.celery_app'
]

# Create Celery application
app = Celery(
    'jps_prospect_aggregate',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=TASK_MODULES
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=int(os.getenv("WORKER_PREFETCH_MULTIPLIER", 1)),
    worker_max_tasks_per_child=int(os.getenv("WORKER_MAX_TASKS_PER_CHILD", 100)),
    
    # Result settings
    result_expires=int(os.getenv("RESULT_EXPIRES", 3600)),
    
    # Beat settings
    beat_schedule_filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp', 'celerybeat-schedule'),
    
    # Task retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Task time limits
    task_time_limit=3600,
    task_soft_time_limit=3000
)

# Configure Celery beat schedule
app.conf.beat_schedule = {
    'acquisition-gateway-daily': {
        'task': 'src.tasks.scrapers.run_acquisition_gateway',
        'schedule': 3600 * 24,  # Run daily
        'args': (True,),  # Force argument
    },
    'ssa-contract-forecast-daily': {
        'task': 'src.tasks.scrapers.run_ssa_contract_forecast',
        'schedule': 3600 * 24,  # Run daily
        'args': (True,),  # Force argument
    },
    'check-all-scrapers': {
        'task': 'src.tasks.health.check_all_scrapers',
        'schedule': 3600,  # Run hourly
    }
}

# Celery signal handlers
@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    """Log task failures."""
    logger.error(f"Task {sender.name}[{task_id}] failed: {exception}")

@task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    """Log task successes."""
    logger.info(f"Task {sender.name} completed successfully")

@worker_ready.connect
def handle_worker_ready(**kwargs):
    """Log when a worker is ready."""
    logger.info("Celery worker is ready")

# Debug task to verify Celery is working
@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery."""
    logger.info(f"Debug task running: {self.request.id}")
    return "Celery is working!"

if __name__ == '__main__':
    logger.info("Starting Celery worker")
    app.start() 