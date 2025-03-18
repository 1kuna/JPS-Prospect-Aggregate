"""Base task classes for all background tasks."""

import logging
import traceback
from datetime import datetime

from celery import Task
from sqlalchemy.exc import SQLAlchemyError

from src.celery_app import celery_app
from src.database.db_session_manager import session_scope
from src.database.models import ScraperStatus
from src.exceptions import (
    ScraperError, NetworkError, TimeoutError, DatabaseError, BaseAppException
)
from src.utils.logging import get_component_logger

logger = get_component_logger('tasks.base')

class BaseTask(Task):
    """Base class for all Celery tasks with enhanced error handling."""
    
    abstract = True  # Celery won't register this as a task
    task_type = "generic"  # Override in subclasses: "scraper", "health_check", etc.
    name = None  # Task name, override in subclasses
    max_retries = 3
    retry_delay = 300
    
    def __init__(self):
        self.logger = get_component_logger(f'tasks.{self.name}' if self.name else 'tasks.unknown')
    
    def calculate_collection_time(self, start_time):
        """Calculate the time elapsed since start_time."""
        end_time = datetime.utcnow()
        return (end_time - start_time).total_seconds()
    
    def format_result(self, status, message, **kwargs):
        """Format a standardized task result dictionary."""
        result = {
            "status": status,
            "message": message,
            "task_id": self.request.id
        }
        result.update(kwargs)
        return result
    
    def handle_error(self, error, context_name):
        """Handle and log a task error, returning a formatted error result."""
        self.logger.exception(f"Unexpected error in {context_name}: {error}")
        self.logger.error(traceback.format_exc())
        return self.format_result(
            "error",
            f"Unexpected error: {str(error)}",
            error_code="TASK_ERROR"
        )
    
    def __call__(self, *args, **kwargs):
        """Override the Task.__call__ method to add error handling."""
        try:
            # Call the original method
            return super().__call__(*args, **kwargs)
        except (NetworkError, TimeoutError) as e:
            self.logger.error(f"Network error in {self.name}: {str(e)}")
            # Retry network errors
            raise self.retry(exc=e)
        except DatabaseError as e:
            self.logger.error(f"Database error in {self.name}: {str(e)}")
            # Retry database errors
            raise self.retry(exc=e)
        except (ScraperError, BaseAppException) as e:
            self.logger.error(f"Application error in {self.name}: {str(e)}")
            # Retry application errors
            raise self.retry(exc=e)
        except Exception as e:
            # Log unexpected errors but don't retry
            return self.handle_error(e, self.name)
    
    @classmethod
    def register(cls):
        """Register this task with Celery."""
        return celery_app.register_task(cls())


class ScraperTask(BaseTask):
    """Base class for scraper tasks."""
    
    abstract = True
    task_type = "scraper"
    
    def update_status(self, status, error_message=None):
        """Update the scraper status in the database."""
        try:
            with session_scope() as session:
                # Find the data source by name
                from src.database.models import DataSource
                data_source = session.query(DataSource).filter(
                    DataSource.name.like(f'%{self.name}%')
                ).first()
                
                if not data_source:
                    self.logger.warning(f"Data source not found for {self.name}")
                    return
                
                # Find or create status record
                status_record = session.query(ScraperStatus).filter(
                    ScraperStatus.source_id == data_source.id
                ).first()
                
                if not status_record:
                    status_record = ScraperStatus(
                        source_id=data_source.id,
                        status=status,
                        error_message=error_message,
                        last_checked=datetime.utcnow(),
                        subtask_id=self.request.id
                    )
                    session.add(status_record)
                else:
                    status_record.status = status
                    status_record.error_message = error_message
                    status_record.last_checked = datetime.utcnow()
                    status_record.subtask_id = self.request.id
                
                session.commit()
                self.logger.info(f"Updated status for {self.name} to {status}")
        
        except Exception as e:
            self.logger.error(f"Error updating status: {str(e)}")
    
    def count_proposals(self, session, source_id=None):
        """Count proposals for this scraper's data source."""
        try:
            from src.database.models import Proposal, DataSource
            
            if source_id:
                return session.query(Proposal).filter(
                    Proposal.source_id == source_id
                ).count()
            
            # Find data source by name
            data_source = session.query(DataSource).filter(
                DataSource.name.like(f'%{self.name}%')
            ).first()
            
            if data_source:
                # Update last_scraped timestamp
                data_source.last_scraped = datetime.utcnow()
                return session.query(Proposal).filter(
                    Proposal.source_id == data_source.id
                ).count()
            
            return 0
        except Exception as e:
            self.logger.error(f"Error counting proposals: {str(e)}")
            return 0


class HealthCheckTask(BaseTask):
    """Base class for health check tasks."""
    
    abstract = True
    task_type = "health_check"


class ForceCollectTask(BaseTask):
    """Task to force collection from a specific source."""
    
    abstract = True
    task_type = "force_collect" 