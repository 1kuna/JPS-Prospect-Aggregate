# Utilities

This directory contains utility modules used throughout the application.

## Modules

- `logger.py`: Centralized logging system using Loguru
- `file_utils.py`: File handling utilities
- `db_utils.py`: Database utility functions

## Logging System

We use the [Loguru](https://github.com/Delgan/loguru) library for logging throughout the application. It provides a simple yet powerful API with many advanced features.

### Basic Usage

For most components, use the centralized logger with contextual binding:

```python
from src.utils.logger import logger

# Create a component-specific logger
logger = logger.bind(name="api.routes")
logger.info("Request received")
```

### Scraper Logging

For scrapers, use the same approach but add the "scraper" prefix to the name:

```python
from src.utils.logger import logger

# Create a scraper-specific logger
logger = logger.bind(name="scraper.ssa_contract_forecast")
logger.info("Starting scrape operation")

# Enable debug mode conditionally
if debug_mode:
    logger.debug("Debug information")
```

### Adding Context to Logs

You can add additional context to logs:

```python
# Add request ID to logs
request_logger = logger.bind(request_id="1234-5678")
request_logger.info("Processing request")
```

### Log Cleanup

Use the `cleanup_logs` function to manage log file rotation:

```python
from src.utils.logger import cleanup_logs

# Clean up old log files, keeping the 5 most recent
cleanup_logs(keep_count=5)
```

For detailed migration information, see `LOGURU_MIGRATION.md`.

## File Utilities

The `file_utils.py` module provides functions for common file operations:

- `ensure_directory`: Create a directory if it doesn't exist
- `find_files`: Find files matching a pattern with a minimum size
- `clean_old_files`: Remove old files while keeping a specified number of the most recent
- `safe_file_copy`: Safely copy a file, ensuring the destination directory exists

## Database Utilities

The `db_utils.py` module provides utilities for database operations:

- Connection management
- Query execution
- Transaction handling
- Error recovery