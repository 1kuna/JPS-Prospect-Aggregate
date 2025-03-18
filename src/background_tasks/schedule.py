"""
Schedule module for generating the Celery beat schedule dynamically.

This module provides functions for generating the Celery beat schedule based on
registered tasks. It allows for dynamic schedule generation based on configuration
and registered tasks.
"""

import logging
from src.config import active_config
from src.utils.logging import get_component_logger

# Set up logging using the centralized utility
logger = get_component_logger('tasks.schedule')

def generate_beat_schedule(task_registry):
    """
    Generate the Celery beat schedule based on registered tasks.
    
    Args:
        task_registry: TaskRegistry instance
        
    Returns:
        dict: Celery beat schedule
    """
    logger.info("Generating beat schedule")
    
    beat_schedule = {}
    
    # Add scraper tasks to the schedule
    for scraper_name, task in task_registry.scraper_tasks.items():
        task_name = f"run_{scraper_name.lower().replace(' ', '_')}_scraper_task"
        beat_schedule[task_name] = {
            'task': f'src.background_tasks.scraper_tasks.{task_name}',
            'schedule': active_config.SCRAPE_INTERVAL_HOURS * 3600,  # Convert hours to seconds
            'args': (),
            'options': {'expires': 3600}  # Task expires if not executed within 1 hour
        }
        logger.info(f"Added {task_name} to beat schedule with interval {active_config.SCRAPE_INTERVAL_HOURS} hours")
    
    # Add health check tasks to the schedule
    for check_name, task in task_registry.health_check_tasks.items():
        task_name = f"check_{check_name.lower().replace(' ', '_')}_task"
        beat_schedule[task_name] = {
            'task': f'src.background_tasks.health_check_tasks.{task_name}',
            'schedule': active_config.HEALTH_CHECK_INTERVAL_MINUTES * 60,  # Convert minutes to seconds
            'args': (),
            'options': {'expires': 600}  # Task expires if not executed within 10 minutes
        }
        logger.info(f"Added {task_name} to beat schedule with interval {active_config.HEALTH_CHECK_INTERVAL_MINUTES} minutes")
    
    return beat_schedule 