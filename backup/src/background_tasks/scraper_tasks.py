"""Celery tasks for running scrapers."""

from datetime import datetime

from src.background_tasks.base_task import ScraperTask, ForceCollectTask
from src.background_tasks.decorators import celery_task
from src.utils.logger import logger
from src.database.db import session_scope
from src.data_collectors.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from src.data_collectors.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper
from src.exceptions import ScraperError

# Set up logging
logger = logger.bind(name="tasks.scraper")

@celery_task(task_type="scraper")
class AcquisitionGatewayScraperTask(ScraperTask):
    """Task to run the Acquisition Gateway scraper."""
    
    name = "Acquisition Gateway"
    
    def run(self, force=True):
        """Run the Acquisition Gateway scraper."""
        self.logger.info(f"Starting {self.name} scraper task")
        start_time = datetime.utcnow()
        
        # Update status to running
        self.update_status("running")
        
        try:
            # Run the scraper
            success = run_acquisition_gateway_scraper(force=force)
            
            if success:
                # Calculate collection time
                collection_time = self.calculate_collection_time(start_time)
                
                with session_scope() as session:
                    proposal_count = self.count_proposals(session)
                    
                # Update status to completed
                self.update_status("completed")
                
                self.logger.info(f"Scraper completed successfully. Collected {proposal_count} proposals in {collection_time:.2f} seconds")
                return self.format_result(
                    "success",
                    "Scraper completed successfully",
                    proposals_collected=proposal_count,
                    collection_time=collection_time
                )
            else:
                # Update status to error
                self.update_status("error", f"{self.name} scraper failed without specific error")
                
                # Raise error to trigger retry
                raise ScraperError(f"{self.name} scraper failed without specific error")
        
        except Exception as e:
            # Update status to error
            self.update_status("error", str(e))
            raise

@celery_task(task_type="scraper")
class SSAContractForecastScraperTask(ScraperTask):
    """Task to run the SSA Contract Forecast scraper."""
    
    name = "SSA Contract Forecast"
    
    def run(self, force=True):
        """Run the SSA Contract Forecast scraper."""
        self.logger.info(f"Starting {self.name} scraper task")
        start_time = datetime.utcnow()
        
        # Update status to running
        self.update_status("running")
        
        try:
            # Run the scraper
            success = run_ssa_contract_forecast_scraper(force=force)
            
            if success:
                # Calculate collection time
                collection_time = self.calculate_collection_time(start_time)
                
                with session_scope() as session:
                    proposal_count = self.count_proposals(session)
                    
                # Update status to completed
                self.update_status("completed")
                
                self.logger.info(f"Scraper completed successfully. Collected {proposal_count} proposals in {collection_time:.2f} seconds")
                return self.format_result(
                    "success",
                    "Scraper completed successfully",
                    proposals_collected=proposal_count,
                    collection_time=collection_time
                )
            else:
                # Update status to error
                self.update_status("error", f"{self.name} scraper failed without specific error")
                
                # Raise error to trigger retry
                raise ScraperError(f"{self.name} scraper failed without specific error")
        
        except Exception as e:
            # Update status to error
            self.update_status("error", str(e))
            raise

@celery_task(task_type="force_collect")
class ForceCollectTaskImpl(ForceCollectTask):
    """Task to force collection from a specific source."""
    
    name = "Force Collect"
    
    def run(self, source_id=None):
        """
        Force collection from a specific source.
        
        Args:
            source_id: ID of the data source to collect from, or None for all
        """
        self.logger.info(f"Starting force collect task for source_id={source_id}")
        
        try:
            if source_id is None:
                # Run all scrapers
                self.logger.info("Running all scrapers")
                # Import group here to avoid circular imports
                from celery import group
                
                # Create a group with all scraper tasks
                task_group = group([
                    AcquisitionGatewayScraperTask().s(force=True),
                    SSAContractForecastScraperTask().s(force=True)
                ])
                
                # Run the tasks in parallel
                result = task_group.apply_async()
                
                return self.format_result(
                    "success",
                    "All scrapers task started successfully",
                    data={"group_id": result.id}
                )
            
            # Find the appropriate source
            with session_scope() as session:
                from src.database.models import DataSource
                data_source = session.query(DataSource).filter_by(id=source_id).first()
                
                if not data_source:
                    error_msg = f"Data source with ID {source_id} not found"
                    self.logger.error(error_msg)
                    return self.format_result(
                        "error",
                        error_msg,
                        error_code="RESOURCE_NOT_FOUND"
                    )
                
                # Choose the appropriate task based on source name
                if "Acquisition Gateway" in data_source.name:
                    result = AcquisitionGatewayScraperTask().delay(force=True)
                elif "SSA Contract Forecast" in data_source.name:
                    result = SSAContractForecastScraperTask().delay(force=True)
                else:
                    error_msg = f"No scraper available for data source: {data_source.name}"
                    self.logger.error(error_msg)
                    return self.format_result(
                        "error",
                        error_msg,
                        error_code="SCRAPER_ERROR"
                    )
                
                return self.format_result(
                    "success",
                    f"Scraper task for {data_source.name} started successfully",
                    data={"task_id": result.id}
                )
                
        except Exception as e:
            return self.handle_error(e, "force collect task") 