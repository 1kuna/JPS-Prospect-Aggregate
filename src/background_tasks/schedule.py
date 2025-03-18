"""
Schedule module for generating the Celery beat schedule dynamically.

This module provides functions for generating the Celery beat schedule based on
registered tasks. It allows for dynamic schedule generation based on configuration
and registered tasks.
"""

from src.config import active_config
from src.utils.logging import get_component_logger

# Set up logging
logger = get_component_logger('tasks.schedule')

def generate_beat_schedule(task_registry):
    """Generate the Celery beat schedule."""
    logger.info("Generating beat schedule")
    
    beat_schedule = {}
    
    # Add scraper tasks
    for scraper_name, task in task_registry.scraper_tasks.items():
        task_name = f"run_{scraper_name.lower().replace(' ', '_')}_scraper_task"
        beat_schedule[task_name] = {
            'task': task.name,  # Use the task's full name
            'schedule': active_config.SCRAPE_INTERVAL_HOURS * 3600,
            'args': (True,),  # force=True
            'options': {'expires': 3600}
        }
        logger.info(f"Added {task_name} to beat schedule")
    
    # Add health check tasks
    for check_name, task in task_registry.health_check_tasks.items():
        task_name = f"check_{check_name.lower().replace(' ', '_')}_task"
        beat_schedule[task_name] = {
            'task': task.name,  # Use the task's full name
            'schedule': active_config.HEALTH_CHECK_INTERVAL_MINUTES * 60,
            'args': (),
            'options': {'expires': 600}
        }
        logger.info(f"Added {task_name} to beat schedule")
    
    return beat_schedule 