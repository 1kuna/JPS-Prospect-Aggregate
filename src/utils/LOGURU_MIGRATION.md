# Loguru Migration Guide

This guide provides instructions for migrating from the previous custom logging system to Loguru.

## Overview

We've simplified our logging system by switching to [Loguru](https://github.com/Delgan/loguru), a third-party library that provides a much cleaner API while maintaining all the functionality we need.

## New Logger Usage

### Basic Usage

```python
from src.utils.logger import logger

# Simple logging
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

# Log an exception with traceback
try:
    1/0
except Exception as e:
    logger.exception(f"An error occurred: {e}")
```

### Component-specific Logging

To create a component-specific logger, use `bind()` with a name:

```python
from src.utils.logger import logger

# Create a component-specific logger
component_logger = logger.bind(name="component.name")
component_logger.info("This message comes from a specific component")
```

### Migration Examples

#### Before (with old logging system):

```python
from src.utils.logging import get_component_logger

# Set up logging with the centralized utility
logger = get_component_logger('my_component')
logger.info("Component initialized")
```

#### After (with Loguru):

```python
from src.utils.logger import logger

# Set up logging with the centralized utility
logger = logger.bind(name="my_component")
logger.info("Component initialized")
```

### Scraper-specific Logging

For scrapers, use a similar pattern:

#### Before:

```python
from src.utils.logging import get_scraper_logger

logger = get_scraper_logger('acquisition_gateway', debug_mode=True)
logger.info("Scraper initialized")
```

#### After:

```python
from src.utils.logger import logger

logger = logger.bind(name="scraper.acquisition_gateway")
logger.info("Scraper initialized")
if debug_mode:
    logger.debug("Debug mode enabled")
```

### Cleanup Functions

The log cleanup functions have also been updated:

#### Before:

```python
from src.utils.logging import cleanup_all_logs

cleanup_results = cleanup_all_logs(logs_dir, keep_count=3)
```

#### After:

```python
from src.utils.logger import cleanup_logs

cleanup_results = cleanup_logs(logs_dir, keep_count=3)
```

## Benefits of Loguru

1. **Simpler API**: Loguru provides a much cleaner and more intuitive API
2. **Better Exception Handling**: Automatic traceback formatting
3. **Contextual Binding**: Easy to add context to logs
4. **Colorized Console Output**: Better readability in development
5. **Built-in Rotation and Retention**: No need for custom handlers
6. **Performance**: Loguru is optimized for performance

## Advanced Features

### Adding Context to Logs

You can add contextual information to logs:

```python
# Add request ID to all subsequent log messages
request_logger = logger.bind(request_id="1234-5678")
request_logger.info("Processing request")

# Add user information
user_logger = request_logger.bind(user_id="user123")
user_logger.info("User logged in")
```

### Temporarily Change Log Level

```python
# Temporarily enable DEBUG level for a specific block of code
with logger.contextualize(level="DEBUG"):
    logger.debug("This debug message will be shown")
```

For more advanced features, see the [Loguru documentation](https://github.com/Delgan/loguru). 