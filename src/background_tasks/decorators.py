"""Decorators for task registration."""

from functools import wraps
from src.background_tasks.registry import task_registry

def celery_task(task_type=None):
    """
    Decorator to register a task with the task registry.
    
    Args:
        task_type: Type of task (scraper, health_check, etc.)
    
    Example:
        @celery_task(task_type="scraper")
        class MyScraperTask(ScraperTask):
            name = "My Scraper"
            ...
    """
    def decorator(cls):
        # Register the task with Celery
        task_instance = cls.register()
        
        # Register with our task registry
        if task_type == "scraper":
            task_registry.register_scraper_task(cls.name, task_instance)
        elif task_type == "health_check":
            task_registry.register_health_check_task(cls.name, task_instance)
        elif task_type == "force_collect":
            task_registry.register_force_collect_task(task_instance)
        
        return cls
    
    return decorator 