# Utilities

This directory contains utility modules used throughout the application. These utilities provide common functionality that is shared across different components.

## Logging System

### Overview

The application uses a unified, flexible logging system that provides consistent logging across all components. The logging system is defined in `logging.py` and offers:

- **Single Interface**: All logging needs are served through a single primary function (`get_logger`) with specialized convenience functions for common use cases
- **Consistent Configuration**: Logging format, level, and behavior are consistent across the application
- **Categorized Loggers**: Loggers are organized by category (component, scraper, system) for better management
- **Environment-Aware**: Default log levels adapt based on the environment (development, testing, production)
- **File and Console Output**: All logs go to both files and console by default
- **Log Management**: Built-in functions for log rotation and cleanup

### Usage

#### Basic Usage

For most components, use the `get_component_logger` function:

```python
from src.utils.logging import get_component_logger

# Create a logger for your component
logger = get_component_logger('api.routes')

# Use the logger
logger.info("Processing request")
logger.error("An error occurred", exc_info=True)
```

#### Scraper Usage

For scrapers, use the specialized `get_scraper_logger`:

```python
from src.utils.logging import get_scraper_logger

# Create a logger for a scraper, optionally in debug mode
logger = get_scraper_logger('ssa_contract_forecast', debug_mode=True)

# Use the logger
logger.debug("Scraper details") # Only visible in debug mode
logger.info("Scraper status")
```

#### Advanced Usage

For more control, use the core `get_logger` function directly:

```python
from src.utils.logging import get_logger, CATEGORY_SYSTEM

# Create a custom logger
logger = get_logger(
    name="custom_logger",
    category=CATEGORY_SYSTEM,
    log_file="custom.log",
    detailed_format=True,
    console=True
)
```

### Log Management

The logging module also provides functions for log rotation and cleanup:

```python
from src.utils.logging import cleanup_all_logs

# Clean up old log files, keeping the 5 most recent for each type
cleanup_all_logs(keep_count=5)
```

## File Utilities

The `file_utils.py` module provides functions for common file operations:

- `ensure_directories`: Create directories if they don't exist
- `cleanup_files`: Remove old files while keeping a specified number of the most recent
- `get_file_size`: Get human-readable file size
- `download_file`: Download a file from a URL with progress tracking

## Database Utilities

The `db_utils.py` module provides utilities for database operations:

- Connection management
- Query execution
- Transaction handling
- Error recovery

## Import Utilities

The `imports.py` module contains utilities for dynamic importing and module discovery:

- `import_module_from_path`: Import a module from a file path
- `discover_modules`: Discover all modules in a package matching criteria 