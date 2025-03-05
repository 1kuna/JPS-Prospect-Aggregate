import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Redis URL from environment or use default
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

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
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks
    
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Beat settings (for scheduled tasks)
    beat_schedule={
        'run-acquisition-gateway-scraper': {
            'task': 'src.tasks.scraper_tasks.run_acquisition_gateway_scraper_task',
            'schedule': int(os.getenv("SCRAPE_INTERVAL_HOURS", 24)) * 3600,  # Convert hours to seconds
            'args': (),
            'options': {'expires': 3600}  # Task expires if not executed within 1 hour
        },
        'run-ssa-contract-forecast-scraper': {
            'task': 'src.tasks.scraper_tasks.run_ssa_contract_forecast_scraper_task',
            'schedule': int(os.getenv("SCRAPE_INTERVAL_HOURS", 24)) * 3600,  # Convert hours to seconds
            'args': (),
            'options': {'expires': 3600}  # Task expires if not executed within 1 hour
        },
        'check-all-scrapers': {
            'task': 'src.tasks.health_check_tasks.check_all_scrapers_task',
            'schedule': int(os.getenv("HEALTH_CHECK_INTERVAL_MINUTES", 10)) * 60,  # Convert minutes to seconds
            'args': (),
            'options': {'expires': 600}  # Task expires if not executed within 10 minutes
        }
    }
)

if __name__ == '__main__':
    celery_app.start() 