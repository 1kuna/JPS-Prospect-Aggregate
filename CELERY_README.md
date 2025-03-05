# JPS Prospect Aggregate with Celery

This document provides instructions for running the JPS Prospect Aggregate application with Celery for task queuing.

## Prerequisites

- Python 3.8 or higher
- Redis server (for Celery broker and result backend)
- All dependencies listed in requirements.txt

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/JPS-Prospect-Aggregate.git
   cd JPS-Prospect-Aggregate
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Install and start Redis:
   - On macOS: `brew install redis && brew services start redis`
   - On Ubuntu: `sudo apt-get install redis-server && sudo systemctl start redis-server`
   - On Windows: Download and install from https://github.com/microsoftarchive/redis/releases

5. Copy the example environment file and configure it:
   ```
   cp .env.example .env
   ```
   Edit the `.env` file to set your configuration values.

## Running the Application

### Quick Start (Recommended)

We've provided scripts to start all components with a single command:

**Windows:**
```
start_all.bat
```

**Mac/Linux:**
```
./start_all.sh
```

These scripts will:
1. Check for and create a virtual environment if needed
2. Install dependencies if needed
3. Start the Flask application
4. Start the Celery worker
5. Start the Celery beat scheduler
6. Start Flower for monitoring
7. Automatically restart any component if it crashes

### Manual Start

If you prefer to start components individually:

#### Start the Flask Web Application

```
python app.py
```

This will start the Flask web application on the host and port specified in your `.env` file (default: http://0.0.0.0:5000).

#### Start Celery Workers

In a separate terminal, start the Celery worker:

```
celery -A src.celery_app worker --loglevel=info
```

#### Start Celery Beat (for scheduled tasks)

In another terminal, start Celery Beat:

```
celery -A src.celery_app beat --loglevel=info
```

#### Start Flower (optional, for monitoring Celery tasks)

In another terminal, start Flower:

```
celery -A src.celery_app flower --port=5555
```

You can then access the Flower dashboard at http://localhost:5555 to monitor your Celery tasks.

## Architecture

The application uses the following components:

- **Flask**: Web application framework
- **SQLAlchemy**: ORM for database access
- **Celery**: Task queue for asynchronous and scheduled tasks
- **Redis**: Message broker and result backend for Celery
- **Playwright**: Browser automation for web scraping

## Task Types

The application uses Celery for the following types of tasks:

1. **Scraper Tasks**: Collect data from various sources
   - Acquisition Gateway Forecast
   - SSA Contract Forecast

2. **Health Check Tasks**: Monitor the health of scrapers
   - Check if scrapers can connect to their target sites
   - Update status in the database

## Environment Variables

The application uses the following environment variables:

- `HOST`: Host to run the Flask application on (default: 0.0.0.0)
- `PORT`: Port to run the Flask application on (default: 5000)
- `DEBUG`: Enable debug mode (default: False)
- `DATABASE_URL`: SQLAlchemy database URL (default: sqlite:///data/proposals.db)
- `SQL_ECHO`: Enable SQL query logging (default: False)
- `SCRAPE_INTERVAL_HOURS`: Interval for scheduled scraping in hours (default: 24)
- `HEALTH_CHECK_INTERVAL_MINUTES`: Interval for health checks in minutes (default: 10)
- `REDIS_URL`: Redis URL for Celery (default: redis://localhost:6379/0)
- `CELERY_BROKER_URL`: Celery broker URL (default: redis://localhost:6379/0)
- `CELERY_RESULT_BACKEND`: Celery result backend URL (default: redis://localhost:6379/0)

## Troubleshooting

### Redis Connection Issues

If you encounter Redis connection issues, make sure Redis is running:

```
redis-cli ping
```

Should return `PONG`. If not, restart Redis:

- On macOS: `brew services restart redis`
- On Ubuntu: `sudo systemctl restart redis-server`
- On Windows: Restart the Redis service

### Celery Worker Not Starting

If the Celery worker fails to start, check:

1. Redis is running
2. Environment variables are set correctly
3. Python path includes the project root

### Database Connection Issues

If you encounter database connection issues:

1. Check the `DATABASE_URL` in your `.env` file
2. Ensure the database file exists and is accessible
3. Try reconnecting using the API endpoint: `/api/reconnect-db` 