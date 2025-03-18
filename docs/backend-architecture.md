# Backend Architecture

This document provides a comprehensive overview of the backend architecture for the JPS-Prospect-Aggregate project.

## Table of Contents

- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [Core Components](#core-components)
  - [Flask Application](#flask-application)
  - [Database](#database)
  - [API Endpoints](#api-endpoints)
  - [Background Tasks](#background-tasks)
  - [Data Scrapers](#data-scrapers)
- [Data Flow](#data-flow)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Deployment](#deployment)

## Overview

The JPS-Prospect-Aggregate backend is built with Python using Flask as the web framework, SQLAlchemy for database operations, and Celery for background task processing. The backend serves as both an API server for the React frontend and a data collection system that scrapes proposal data from various sources.

## Directory Structure

```
src/
├── dashboard/              # Flask web application
│   ├── blueprints/         # Flask blueprints for routes
│   │   ├── api/            # API endpoints
│   │   ├── data_sources/   # Data source management
│   │   └── main/           # Main routes
│   ├── static/             # Static assets
│   ├── templates/          # HTML templates
│   ├── factory.py          # Flask application factory
│   └── __init__.py
├── database/               # Database models and connection management
│   ├── models.py           # SQLAlchemy models
│   ├── db_session_manager.py  # Session management
│   ├── connection_pool.py  # Database connection pooling
│   ├── init_db.py          # Database initialization
│   ├── download_tracker.py # Track download progress
│   └── __init__.py
├── scrapers/               # Web scrapers for data collection
│   ├── base_scraper.py     # Base scraper class
│   ├── acquisition_gateway.py  # Acquisition Gateway scraper
│   ├── ssa_contract_forecast.py  # SSA Contract Forecast scraper
│   ├── health_check.py     # Scraper health monitoring
│   └── __init__.py
├── tasks/                  # Celery background tasks
│   ├── scraper_tasks.py    # Tasks for running scrapers
│   ├── health_check_tasks.py  # Tasks for health checks
│   └── __init__.py
├── utils/                  # Utility functions
├── config.py               # Configuration settings
├── celery_app.py           # Celery configuration
├── exceptions.py           # Custom exceptions
└── __init__.py
```

## Core Components

### Flask Application

The backend uses Flask as the web framework, with a factory pattern for creating the application instance. This allows for flexible configuration and easier testing.

#### Application Factory

The `create_app` function in `src/dashboard/factory.py` creates and configures the Flask application:

```python
def create_app(config=None):
    """Application factory for creating Flask app instances."""
    # Create and configure the app
    app = Flask(__name__)
    
    # Configure Flask to redirect URLs with trailing slashes to URLs without trailing slashes
    app.url_map.strict_slashes = False
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Load default configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24).hex())
    
    # Apply any custom configuration
    if config:
        app.config.update(config)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # ... routes for serving static files ...
    
    return app
```

#### Blueprints

The application is organized into blueprints for better code organization:

- **API Blueprint**: Handles API endpoints for the frontend
- **Data Sources Blueprint**: Manages data source configuration
- **Main Blueprint**: Handles main routes and views

### Database

The application uses SQLAlchemy as an ORM (Object-Relational Mapper) to interact with the database.

#### Models

The main database models are defined in `src/database/models.py`:

1. **DataSource**: Represents a source of proposal data
   ```python
   class DataSource(Base):
       __tablename__ = 'data_sources'
       
       id = Column(Integer, primary_key=True)
       name = Column(String(100), nullable=False)
       url = Column(String(255), nullable=False)
       description = Column(Text, nullable=True)
       last_scraped = Column(DateTime, nullable=True)
       
       proposals = relationship("Proposal", back_populates="source")
       status_checks = relationship("ScraperStatus", back_populates="source")
   ```

2. **Proposal**: Stores proposal forecast data
   ```python
   class Proposal(Base):
       __tablename__ = 'proposals'
       
       id = Column(Integer, primary_key=True)
       source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False)
       external_id = Column(String(100), nullable=True)
       title = Column(String(255), nullable=False)
       agency = Column(String(100), nullable=True)
       # ... additional fields ...
       
       source = relationship("DataSource", back_populates="proposals")
       history = relationship("ProposalHistory", back_populates="proposal")
   ```

3. **ProposalHistory**: Tracks historical proposal data
   ```python
   class ProposalHistory(Base):
       __tablename__ = 'proposal_history'
       
       id = Column(Integer, primary_key=True)
       proposal_id = Column(Integer, ForeignKey('proposals.id'), nullable=False)
       # ... fields similar to Proposal ...
       
       proposal = relationship("Proposal", back_populates="history")
   ```

4. **ScraperStatus**: Tracks scraper health status
   ```python
   class ScraperStatus(Base):
       __tablename__ = 'scraper_status'
       
       id = Column(Integer, primary_key=True)
       source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False)
       status = Column(String(50), nullable=False, default="unknown")
       last_checked = Column(DateTime, nullable=True)
       error_message = Column(Text, nullable=True)
       response_time = Column(Float, nullable=True)
       
       source = relationship("DataSource", back_populates="status_checks")
   ```

#### Session Management

The application uses a session manager to handle database connections:

```python
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

This context manager ensures that sessions are properly closed and transactions are committed or rolled back as appropriate.

### API Endpoints

The API endpoints are defined in `src/api/routes.py`. The main endpoints include:

#### Proposals Endpoint

```python
@api.route('/proposals')
def get_proposals():
    """API endpoint to get proposals with sorting and pagination."""
    # Validate sort parameters
    sort_by = request.args.get("sort_by", "release_date")
    sort_order = request.args.get("sort_order", "desc").lower()
    
    with session_scope() as session:
        # Build and execute query
        query = session.query(Proposal)
        # Apply sorting and pagination
        # ...
        
        return jsonify({
            "status": "success",
            "data": [proposal.to_dict() for proposal in proposals],
            "pagination": pagination_result["pagination"]
        })
```

#### Dashboard Endpoint

```python
@api.route('/dashboard')
def get_dashboard():
    """API endpoint to get dashboard data."""
    with session_scope() as session:
        # Get counts and recent proposals
        # ...
        
        return jsonify({
            "status": "success",
            "data": {
                "counts": {
                    "total_proposals": total_proposals,
                    "total_sources": total_sources
                },
                "recent_proposals": [proposal.to_dict() for proposal in recent_proposals]
            }
        })
```

#### Health Check Endpoint

```python
@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to monitor the application's health."""
    # Check database and Redis connections
    # ...
    
    return jsonify({
        "status": "success",
        "health": {
            "database": db_status,
            "redis": redis_status,
            # ... other health metrics ...
        }
    })
```

### Background Tasks

The application uses Celery for background task processing, particularly for running scrapers and health checks.

#### Celery Configuration

The Celery application is configured in `src/celery_app.py`:

```python
# Define task modules
TASK_MODULES = [
    'src.tasks.scraper_tasks',
    'src.tasks.health_check_tasks'
]

# Define beat schedule
BEAT_SCHEDULE = {
    'run-acquisition-gateway-scraper': {
        'task': 'src.tasks.scraper_tasks.run_acquisition_gateway_scraper_task',
        'schedule': active_config.SCRAPE_INTERVAL_HOURS * 3600,
        'args': (),
        'options': {'expires': 3600}
    },
    # ... other scheduled tasks ...
}

# Create Celery app
celery_app = Celery(
    'jps_prospect_aggregate',
    broker=redis_url,
    backend=redis_url,
    include=TASK_MODULES
)

# Configure Celery
celery_app.conf.update(
    result_expires=3600,
    worker_max_tasks_per_child=200,
    broker_connection_retry_on_startup=True,
    beat_schedule=BEAT_SCHEDULE
)
```

#### Scraper Tasks

Scraper tasks are defined in `src/tasks/scraper_tasks.py`:

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def run_acquisition_gateway_scraper_task(self):
    """Task to run the Acquisition Gateway scraper."""
    try:
        scraper = AcquisitionGatewayScraper()
        result = scraper.run()
        return result
    except Exception as exc:
        self.retry(exc=exc)
```

#### Health Check Tasks

Health check tasks are defined in `src/tasks/health_check_tasks.py`:

```python
@celery_app.task(bind=True)
def check_all_scrapers_task(self):
    """Task to check the health of all scrapers."""
    try:
        health_checker = ScraperHealthChecker()
        result = health_checker.check_all_scrapers()
        return result
    except Exception as exc:
        logger.error(f"Error checking scrapers: {exc}")
        raise
```

### Data Scrapers

The application includes scrapers for collecting proposal data from various sources.

#### Base Scraper

The `BaseScraper` class in `src/scrapers/base_scraper.py` provides common functionality for all scrapers:

```python
class BaseScraper:
    """Base class for all scrapers."""
    
    def __init__(self, source_name, source_url, description=None):
        self.source_name = source_name
        self.source_url = source_url
        self.description = description
        self.logger = logging.getLogger(f"scraper.{source_name}")
    
    def run(self):
        """Run the scraper."""
        try:
            # Get or create data source
            data_source = self._get_or_create_data_source()
            
            # Fetch and process data
            data = self._fetch_data()
            processed_data = self._process_data(data)
            
            # Save data to database
            self._save_data(processed_data, data_source)
            
            # Update last scraped timestamp
            self._update_last_scraped(data_source)
            
            return {
                "status": "success",
                "source": self.source_name,
                "count": len(processed_data)
            }
        except Exception as e:
            self.logger.error(f"Error running scraper: {e}")
            raise
```

#### Specific Scrapers

The application includes specific scrapers for different data sources:

1. **Acquisition Gateway Scraper**: Scrapes proposal data from the Acquisition Gateway
2. **SSA Contract Forecast Scraper**: Scrapes contract forecast data from the Social Security Administration

## Data Flow

1. **Data Collection**: Celery scheduled tasks trigger scrapers to collect data from external sources
2. **Data Processing**: Scrapers process the raw data into a standardized format
3. **Data Storage**: Processed data is stored in the database
4. **API Access**: The frontend accesses the data through the API endpoints
5. **Health Monitoring**: Health check tasks monitor the status of scrapers and the application

## Configuration

The application uses a configuration system defined in `src/config.py` that supports different environments (development, testing, production).

```python
class Config:
    """Base configuration."""
    DEBUG = False
    TESTING = False
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///data/jps_prospect_aggregate.db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", "24"))
    HEALTH_CHECK_INTERVAL_MINUTES = int(os.getenv("HEALTH_CHECK_INTERVAL_MINUTES", "30"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DATABASE_URI = "sqlite:///:memory:"

class ProductionConfig(Config):
    """Production configuration."""
    # Production-specific settings
```

## Error Handling

The application includes a custom exception system defined in `src/exceptions.py`:

```python
class BaseError(Exception):
    """Base class for all custom exceptions."""
    status_code = 500
    error_code = "INTERNAL_ERROR"
    
    def __init__(self, message=None, status_code=None, error_code=None):
        self.message = message or "An unexpected error occurred"
        self.status_code = status_code or self.status_code
        self.error_code = error_code or self.error_code
        super().__init__(self.message)

class ValidationError(BaseError):
    """Exception raised for validation errors."""
    status_code = 400
    error_code = "VALIDATION_ERROR"

class ResourceNotFoundError(BaseError):
    """Exception raised when a resource is not found."""
    status_code = 404
    error_code = "NOT_FOUND"
```

API errors are handled consistently across the application:

```python
@api.errorhandler(BaseError)
def handle_base_error(error):
    """Handle custom exceptions."""
    response = {
        "status": "error",
        "error": {
            "code": error.error_code,
            "message": error.message
        }
    }
    return jsonify(response), error.status_code
```

## Deployment

The application is designed to be deployed in a containerized environment using Docker. The main components that need to be deployed are:

1. **Web Application**: The Flask application that serves the API
2. **Celery Worker**: Processes background tasks
3. **Celery Beat**: Schedules periodic tasks
4. **Redis**: Used as a message broker for Celery
5. **Database**: Stores the application data

A typical deployment might use Docker Compose to orchestrate these services:

```yaml
version: '3'

services:
  web:
    build: .
    command: gunicorn -b 0.0.0.0:5000 'src.dashboard.factory:create_app()'
    environment:
      - DATABASE_URI=postgresql://user:password@db:5432/jps_prospect_aggregate
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "5000:5000"
    depends_on:
      - db
      - redis

  worker:
    build: .
    command: celery -A src.celery_app:celery_app worker --loglevel=info
    environment:
      - DATABASE_URI=postgresql://user:password@db:5432/jps_prospect_aggregate
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  beat:
    build: .
    command: celery -A src.celery_app:celery_app beat --loglevel=info
    environment:
      - DATABASE_URI=postgresql://user:password@db:5432/jps_prospect_aggregate
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  redis:
    image: redis:alpine

  db:
    image: postgres:13
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=jps_prospect_aggregate
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

This deployment configuration ensures that all components of the application are properly orchestrated and can communicate with each other. 