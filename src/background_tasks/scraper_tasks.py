"""Celery tasks for running scrapers."""

# Import from common imports module
import logging
import traceback
from datetime import datetime
from celery import shared_task
from src.database.db_session_manager import session_scope
from src.database.models import DataSource, Proposal

# Import scrapers
from src.data_collectors.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from src.data_collectors.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper

# Import task factory and registries
from src.background_tasks.task_factory import (
    create_scraper_task, 
    create_all_scrapers_task,
    create_force_collect_task
)
from src.data_collectors.registry import scraper_registry
from src.background_tasks.registry import task_registry
from src.utils.logging import get_component_logger

# Set up logging using the centralized utility
logger = get_component_logger('tasks.scraper')

# Register scrapers in the scraper registry
scraper_registry.register_scraper("Acquisition Gateway", run_acquisition_gateway_scraper)
scraper_registry.register_scraper("SSA Contract Forecast", run_ssa_contract_forecast_scraper)

# Create scraper tasks using the factory function
run_acquisition_gateway_scraper_task = create_scraper_task(
    "Acquisition Gateway", 
    run_acquisition_gateway_scraper
)

run_ssa_contract_forecast_scraper_task = create_scraper_task(
    "SSA Contract Forecast", 
    run_ssa_contract_forecast_scraper
)

# Register scraper tasks in the task registry
task_registry.register_scraper_task("Acquisition Gateway", run_acquisition_gateway_scraper_task)
task_registry.register_scraper_task("SSA Contract Forecast", run_ssa_contract_forecast_scraper_task)

# Create and register the all scrapers task
run_all_scrapers_task = create_all_scrapers_task([
    run_acquisition_gateway_scraper_task,
    run_ssa_contract_forecast_scraper_task
])
task_registry.register_all_scrapers_task(run_all_scrapers_task)

# Create and register the force collect task
force_collect_task = create_force_collect_task(
    run_all_scrapers_task,
    {
        "Acquisition Gateway": run_acquisition_gateway_scraper_task,
        "SSA Contract Forecast": run_ssa_contract_forecast_scraper_task
    }
)
task_registry.register_force_collect_task(force_collect_task)

# Export all tasks
__all__ = [
    'run_acquisition_gateway_scraper_task',
    'run_ssa_contract_forecast_scraper_task',
    'run_all_scrapers_task',
    'force_collect_task'
] 