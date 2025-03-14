"""Celery tasks for health checks."""

import logging
from celery import shared_task
from src.data_collectors.health_check import check_all_scrapers, check_acquisition_gateway, check_ssa_contract_forecast
from src.background_tasks.task_factory import create_health_check_task
from src.background_tasks.registry import task_registry

# Set up logging
logger = logging.getLogger(__name__)

# Create health check tasks using the factory function
check_all_scrapers_task = create_health_check_task(
    "all_scrapers", 
    check_all_scrapers
)

check_acquisition_gateway_task = create_health_check_task(
    "acquisition_gateway", 
    check_acquisition_gateway
)

check_ssa_contract_forecast_task = create_health_check_task(
    "ssa_contract_forecast", 
    check_ssa_contract_forecast
)

# Register health check tasks in the task registry
task_registry.register_health_check_task("all_scrapers", check_all_scrapers_task)
task_registry.register_health_check_task("acquisition_gateway", check_acquisition_gateway_task)
task_registry.register_health_check_task("ssa_contract_forecast", check_ssa_contract_forecast_task)

# Export all tasks
__all__ = [
    'check_all_scrapers_task',
    'check_acquisition_gateway_task',
    'check_ssa_contract_forecast_task'
] 