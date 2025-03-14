# Celery Refactoring Documentation

## Overview

This document describes the refactoring of the Celery task system in the JPS Prospect Aggregate application. The refactoring implements a factory pattern for task creation, centralizes task registration, and provides dynamic beat schedule generation.

## Benefits of the Refactoring

- **Reduced Code Duplication**: The factory pattern eliminates duplicate error handling and logging code.
- **Standardized Task Creation**: All tasks follow the same pattern, making it easier to understand and maintain.
- **Centralized Error Handling**: Error handling strategies are defined in one place.
- **Easier to Add New Scrapers**: Just register a new scraper and its tasks will be automatically created.
- **Better Task Discovery**: The task registry makes it easy to discover and manage tasks.
- **Dynamic Beat Schedule**: The beat schedule is generated dynamically based on registered tasks.
- **Improved Testability**: The factory functions and registries can be easily mocked for testing.
- **Separation of Concerns**: Each module has a clear responsibility.

## Architecture

The refactored Celery task system consists of the following components:

### Task Factory (`src/tasks/task_factory.py`)

Provides factory functions for creating standardized Celery tasks:

- `create_scraper_task`: Creates a task for running a scraper
- `create_health_check_task`: Creates a task for running a health check
- `create_all_scrapers_task`: Creates a task for running all scrapers
- `create_force_collect_task`: Creates a task for forcing collection from a specific source

### Task Registry (`src/tasks/registry.py`)

Maintains a registry of all Celery tasks in the application:

- `TaskRegistry`: Class for registering and retrieving tasks
- `task_registry`: Singleton instance of the task registry

### Scraper Registry (`src/scrapers/registry.py`)

Maintains a registry of all scrapers in the application:

- `ScraperRegistry`: Class for registering and retrieving scrapers
- `scraper_registry`: Singleton instance of the scraper registry

### Schedule Generator (`src/tasks/schedule.py`)

Generates the Celery beat schedule dynamically based on registered tasks:

- `generate_beat_schedule`: Function for generating the beat schedule

### Celery Application (`src/celery_app.py`)

Configures the Celery application and sets up the dynamic beat schedule:

- `setup_periodic_tasks`: Sets up periodic tasks using the task registry and dynamic beat schedule

## Implementation Details

### Task Creation

Tasks are created using factory functions that standardize error handling, logging, and task structure:

```python
# Create a scraper task
run_acquisition_gateway_scraper_task = create_scraper_task(
    "Acquisition Gateway", 
    run_acquisition_gateway_scraper
)
```

### Task Registration

Tasks are registered in the task registry for easy discovery and management:

```python
# Register a scraper task
task_registry.register_scraper_task("Acquisition Gateway", run_acquisition_gateway_scraper_task)
```

### Scraper Registration

Scrapers are registered in the scraper registry:

```python
# Register a scraper
scraper_registry.register_scraper("Acquisition Gateway", run_acquisition_gateway_scraper)
```

### Dynamic Beat Schedule

The beat schedule is generated dynamically based on registered tasks:

```python
# Generate the beat schedule
beat_schedule = generate_beat_schedule(task_registry)

# Update the Celery configuration with the beat schedule
sender.conf.beat_schedule = beat_schedule
```

## Adding a New Scraper

To add a new scraper to the system:

1. Create the scraper implementation in `src/scrapers/`
2. Register the scraper in `src/scrapers/registry.py`
3. Create and register the scraper task in `src/tasks/scraper_tasks.py`
4. Create and register the health check task in `src/tasks/health_check_tasks.py`

The beat schedule will be automatically updated to include the new tasks.

## Conclusion

The refactored Celery task system provides a more maintainable, extensible, and standardized approach to task creation and management. It reduces code duplication, centralizes error handling, and makes it easier to add new scrapers to the system. 