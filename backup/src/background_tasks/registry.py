"""
Task registry module for maintaining a registry of all Celery tasks.

This module provides a central registry for all Celery tasks in the application,
making it easy to discover and manage tasks. It also provides a way to dynamically
generate the beat schedule based on the registered tasks.
"""

import logging
from src.utils.logger import logger

# Set up logging using the centralized utility
logger = logger.bind(name="tasks.registry")

class TaskRegistry:
    """Registry for Celery tasks."""
    
    def __init__(self):
        """Initialize the task registry."""
        self.scraper_tasks = {}
        self.health_check_tasks = {}
        self.force_collect_task = None
    
    def register_scraper_task(self, scraper_name, task):
        """
        Register a scraper task.
        
        Args:
            scraper_name (str): Name of the scraper
            task (function): Celery task function
        """
        logger.info(f"Registering scraper task for {scraper_name}")
        self.scraper_tasks[scraper_name] = task
    
    def register_health_check_task(self, check_name, task):
        """
        Register a health check task.
        
        Args:
            check_name (str): Name of the health check
            task (function): Celery task function
        """
        logger.info(f"Registering health check task for {check_name}")
        self.health_check_tasks[check_name] = task
    
    def register_force_collect_task(self, task):
        """
        Register the force collect task.
        
        Args:
            task (function): Celery task function
        """
        logger.info("Registering force collect task")
        self.force_collect_task = task
    
    def get_all_tasks(self):
        """
        Get all registered tasks.
        
        Returns:
            dict: Dictionary of all registered tasks
        """
        all_tasks = {}
        
        # Add scraper tasks
        for name, task in self.scraper_tasks.items():
            all_tasks[f"run_{name.lower().replace(' ', '_')}_scraper_task"] = task
        
        # Add health check tasks
        for name, task in self.health_check_tasks.items():
            all_tasks[f"check_{name.lower().replace(' ', '_')}_task"] = task
        
        # Add force collect task
        if self.force_collect_task:
            all_tasks["force_collect_task"] = self.force_collect_task
        
        return all_tasks
    
    def get_task_by_name(self, task_name):
        """
        Get a task by name.
        
        Args:
            task_name (str): Name of the task
            
        Returns:
            function: Celery task function, or None if not found
        """
        # Check scraper tasks
        for name, task in self.scraper_tasks.items():
            if task_name == f"run_{name.lower().replace(' ', '_')}_scraper_task":
                return task
        
        # Check health check tasks
        for name, task in self.health_check_tasks.items():
            if task_name == f"check_{name.lower().replace(' ', '_')}_task":
                return task
        
        # Check force collect task
        if self.force_collect_task and task_name == "force_collect_task":
            return self.force_collect_task
        
        return None

# Create a singleton instance of the task registry
task_registry = TaskRegistry() 