"""Celery tasks for health checks."""

from src.background_tasks.base_task import HealthCheckTask
from src.background_tasks.decorators import celery_task
from src.utils.logging import get_component_logger
from src.data_collectors.health_check import (
    check_all_scrapers, check_acquisition_gateway, check_ssa_contract_forecast
)

# Set up logging
logger = get_component_logger('tasks.health_check')

@celery_task(task_type="health_check")
class AllScrapersHealthCheckTask(HealthCheckTask):
    """Task to check the health of all scrapers."""
    
    name = "all_scrapers"
    
    def run(self):
        """Check the health of all scrapers."""
        self.logger.info("Starting health check for all scrapers")
        
        try:
            result = check_all_scrapers()
            self.logger.info(f"Health check completed: {result}")
            return self.format_result(
                "success",
                "Health check completed",
                data=result
            )
        except Exception as e:
            return self.handle_error(e, "health check")

@celery_task(task_type="health_check")
class AcquisitionGatewayHealthCheckTask(HealthCheckTask):
    """Task to check the health of the Acquisition Gateway scraper."""
    
    name = "acquisition_gateway"
    
    def run(self):
        """Check the health of the Acquisition Gateway scraper."""
        self.logger.info("Starting health check for Acquisition Gateway")
        
        try:
            result = check_acquisition_gateway()
            self.logger.info(f"Health check completed: {result}")
            return self.format_result(
                "success",
                "Health check completed",
                data=result
            )
        except Exception as e:
            return self.handle_error(e, "health check")

@celery_task(task_type="health_check")
class SSAContractForecastHealthCheckTask(HealthCheckTask):
    """Task to check the health of the SSA Contract Forecast scraper."""
    
    name = "ssa_contract_forecast"
    
    def run(self):
        """Check the health of the SSA Contract Forecast scraper."""
        self.logger.info("Starting health check for SSA Contract Forecast")
        
        try:
            result = check_ssa_contract_forecast()
            self.logger.info(f"Health check completed: {result}")
            return self.format_result(
                "success",
                "Health check completed",
                data=result
            )
        except Exception as e:
            return self.handle_error(e, "health check") 