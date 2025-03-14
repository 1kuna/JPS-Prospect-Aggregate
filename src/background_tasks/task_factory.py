"""
Task factory module for creating standardized Celery tasks.

This module provides factory functions for creating Celery tasks with consistent
error handling, logging, and structure. It implements the factory pattern to reduce
code duplication and standardize task creation across the application.
"""

import logging
import traceback
from datetime import datetime
from functools import wraps

from src.celery_app import celery_app
from src.database.db_session_manager import session_scope
from src.database.models import DataSource, Proposal
from src.exceptions import ScraperError, NetworkError, TimeoutError, DatabaseError

# Set up logging
logger = logging.getLogger(__name__)

# Helper functions to reduce redundancy

def calculate_collection_time(start_time):
    """Calculate the time elapsed since start_time."""
    end_time = datetime.utcnow()
    return (end_time - start_time).total_seconds()

def format_task_result(task_id, status, message, **kwargs):
    """Format a standardized task result dictionary."""
    result = {
        "status": status,
        "message": message,
        "task_id": task_id
    }
    result.update(kwargs)
    return result

def handle_task_error(task_id, error, context_name):
    """Handle and log a task error, returning a formatted error result."""
    logger.exception(f"Unexpected error in {context_name}: {error}")
    logger.error(traceback.format_exc())
    return format_task_result(
        task_id,
        "error",
        f"Unexpected error: {str(error)}",
        error_code="TASK_ERROR"
    )

def count_proposals_for_source(session, source_name=None, source_id=None):
    """Count proposals for a specific source."""
    if source_id:
        return session.query(Proposal).filter(Proposal.source_id == source_id).count()
    elif source_name:
        source = session.query(DataSource).filter(DataSource.name.like(f'%{source_name}%')).first()
        if source:
            return session.query(Proposal).filter(Proposal.source_id == source.id).count()
    return 0

def count_all_proposals(session):
    """Count all proposals across all sources."""
    total = 0
    data_sources = session.query(DataSource).all()
    for source in data_sources:
        source.last_scraped = datetime.utcnow()  # Update last_scraped timestamp
        count = session.query(Proposal).filter(Proposal.source_id == source.id).count()
        total += count
    session.commit()
    return total

# Task factory functions

def create_scraper_task(scraper_name, scraper_func, max_retries=3, retry_delay=300):
    """
    Factory function to create a standardized scraper task.
    
    Args:
        scraper_name (str): Name of the scraper (used for task naming and logging)
        scraper_func (callable): Function that runs the scraper
        max_retries (int): Maximum number of retries for the task
        retry_delay (int): Delay between retries in seconds
        
    Returns:
        function: Decorated Celery task
    """
    task_name = f"src.background_tasks.scraper_tasks.run_{scraper_name.lower().replace(' ', '_')}_scraper_task"
    
    @celery_app.task(bind=True, name=task_name, max_retries=max_retries, default_retry_delay=retry_delay)
    @wraps(scraper_func)
    def task_wrapper(self, force=True):
        """Celery task to run the scraper"""
        logger.info(f"Starting {scraper_name} scraper task")
        task_id = self.request.id
        start_time = datetime.utcnow()
        
        try:
            # Run the scraper with force=True to ensure it runs
            success = scraper_func(force=force)
            
            if success:
                # Calculate collection time and count proposals
                collection_time = calculate_collection_time(start_time)
                
                with session_scope() as session:
                    proposal_count = count_proposals_for_source(session, source_name=scraper_name)
                
                logger.info(f"{scraper_name} scraper completed successfully. Collected {proposal_count} proposals in {collection_time:.2f} seconds")
                return format_task_result(
                    task_id,
                    "success",
                    "Scraper completed successfully",
                    proposals_collected=proposal_count,
                    collection_time=collection_time
                )
            else:
                logger.error(f"{scraper_name} scraper failed")
                # Retry the task if it fails
                raise ScraperError(f"{scraper_name} scraper failed without specific error")
                
        except (NetworkError, TimeoutError) as e:
            logger.error(f"Network error in {scraper_name} scraper task: {str(e)}")
            # These are retryable errors
            self.retry(exc=e)
            
        except DatabaseError as e:
            logger.error(f"Database error in {scraper_name} scraper task: {str(e)}")
            # Database errors are retryable
            self.retry(exc=e)
            
        except ScraperError as e:
            logger.error(f"Scraper error in {scraper_name} scraper task: {str(e)}")
            # Scraper errors are retryable
            self.retry(exc=e)
            
        except Exception as e:
            return handle_task_error(task_id, e, f"{scraper_name} scraper task")
    
    return task_wrapper

def create_health_check_task(check_name, check_func):
    """
    Factory function to create a standardized health check task.
    
    Args:
        check_name (str): Name of the health check (used for task naming and logging)
        check_func (callable): Function that performs the health check
        
    Returns:
        function: Decorated Celery task
    """
    task_name = f"src.background_tasks.health_check_tasks.check_{check_name.lower().replace(' ', '_')}_task"
    
    @celery_app.task(name=task_name)
    @wraps(check_func)
    def task_wrapper():
        """Celery task to check the health of the scraper"""
        logger.info(f"Starting health check task for {check_name}")
        try:
            result = check_func()
            logger.info(f"Health check completed for {check_name}: {result}")
            return format_task_result("success", "Health check completed", result=result)
        except Exception as e:
            logger.exception(f"Error checking {check_name}: {e}")
            return format_task_result("error", str(e))
    
    return task_wrapper

def create_all_scrapers_task(task_list):
    """
    Factory function to create a task that runs all scrapers.
    
    Args:
        task_list (list): List of scraper tasks to run
        
    Returns:
        function: Decorated Celery task
    """
    @celery_app.task(bind=True, name='src.background_tasks.scraper_tasks.run_all_scrapers_task')
    def run_all_scrapers_task(self):
        """Celery task to run all scrapers in parallel"""
        logger.info("Starting all scrapers task")
        task_id = self.request.id
        start_time = datetime.utcnow()
        
        try:
            # Import celery.group here to avoid circular imports
            from celery import group
            
            # Create a group of tasks to run in parallel
            tasks = group([task.s() for task in task_list])
            
            # Run the tasks in parallel
            result = tasks.apply_async()
            
            # Wait for all tasks to complete
            task_results = result.get()
            
            # Calculate collection time and count proposals
            collection_time = calculate_collection_time(start_time)
            
            with session_scope() as session:
                total_proposals = count_all_proposals(session)
            
            logger.info(f"All scrapers completed. Collected {total_proposals} proposals in {collection_time:.2f} seconds")
            return format_task_result(
                task_id,
                "success",
                "All scrapers completed",
                results=task_results,
                proposals_collected=total_proposals,
                collection_time=collection_time
            )
        except Exception as e:
            return handle_task_error(task_id, e, "all scrapers task")
    
    return run_all_scrapers_task

def create_force_collect_task(all_scrapers_task, scraper_registry):
    """
    Factory function to create a task that forces collection from a specific source.
    
    Args:
        all_scrapers_task (function): Task that runs all scrapers
        scraper_registry (dict): Registry of scraper tasks by source name
        
    Returns:
        function: Decorated Celery task
    """
    @celery_app.task(bind=True, name='src.background_tasks.scraper_tasks.force_collect_task')
    def force_collect_task(self, source_id=None):
        """
        Celery task to force collection from a specific source.
        
        Args:
            source_id (int, optional): ID of the data source to collect from.
                If None, collect from all sources.
        """
        logger.info(f"Starting force collect task for source_id={source_id}")
        task_id = self.request.id
        
        try:
            if source_id is None:
                # Run all scrapers
                return all_scrapers_task.delay().get()
            
            # Get the data source
            with session_scope() as session:
                data_source = session.query(DataSource).filter(DataSource.id == source_id).first()
                
                if not data_source:
                    error_msg = f"Data source with ID {source_id} not found"
                    logger.error(error_msg)
                    return format_task_result(
                        task_id,
                        "error",
                        error_msg,
                        error_code="RESOURCE_NOT_FOUND"
                    )
                
                # Find the appropriate scraper task based on the data source name
                for source_name, task in scraper_registry.items():
                    if source_name in data_source.name:
                        return task.delay().get()
                
                error_msg = f"No scraper available for data source: {data_source.name}"
                logger.error(error_msg)
                return format_task_result(
                    task_id,
                    "error",
                    error_msg,
                    error_code="SCRAPER_ERROR"
                )
                    
        except Exception as e:
            return handle_task_error(task_id, e, "force collect task")
    
    return force_collect_task 