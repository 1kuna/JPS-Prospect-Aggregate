# JPS Proposal Forecast Aggregator

A dashboard application that scrapes data from various proposal forecast sites and organizes them into a searchable, sortable dashboard.

## Features

- Automated scraping of proposal forecast data from government websites
- Data storage in a structured SQLite database
- Web-based dashboard for viewing and analyzing proposal opportunities
- Filtering and sorting capabilities by various criteria
- Scheduled data refresh to keep information current
- Asynchronous task processing with Celery for improved performance

## Current Data Sources

- [Acquisition Gateway Forecast](https://acquisitiongateway.gov/forecast)
- [SSA Contract Forecast](https://www.ssa.gov/osdbu/contract-forecast-intro.html)

## Setup Instructions

### Windows

1. Clone this repository
2. Run the setup script:
   ```
   setup.bat
   ```
   This will:
   - Create a virtual environment
   - Install dependencies
   - Initialize the database

3. Set up environment variables (copy `.env.example` to `.env` and fill in values)
4. Run the application:
   ```
   python app.py
   ```

### Manual Setup (Windows/Mac/Linux)

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Set up environment variables (copy `.env.example` to `.env` and fill in values)
6. Initialize the database:
   ```
   python src/database/init_db.py
   ```
7. Run the application:
   ```
   python app.py
   ```

### Running with Celery (Recommended)

For improved performance and reliability, the application now supports Celery for asynchronous task processing. This allows for:

- Parallel execution of scrapers
- Background processing of health checks
- Improved error handling and task retries
- Task monitoring and management

#### Quick Start with Celery

We've provided scripts to start all components (Flask app, Celery worker, Celery beat, and Flower) with a single command:

**Windows:**
```
start_all.bat
```

**Mac/Linux:**
```
./start_all.sh
```

These scripts will automatically set up the environment and start all necessary components.

For detailed instructions on setting up and running the application with Celery, see [CELERY_README.md](CELERY_README.md).

## Database Management

The project includes scripts for database management:

- `rebuild_db.py`: Rebuilds the database while preserving existing data

## Project Structure

- `app.py`: Main application entry point for the Flask dashboard
- `src/database/init_db.py`: Script to initialize the database
- `src/scrapers/`: Web scraping modules for different data sources
  - `acquisition_gateway.py`: Scraper for Acquisition Gateway Forecast
  - `ssa_contract_forecast.py`: Scraper for SSA Contract Forecast
- `src/database/`: Database models and connection management
- `src/dashboard/`: Flask web application for the dashboard
- `src/scheduler/`: Scheduled tasks for data refresh
- `src/tasks/`: Celery tasks for asynchronous processing
- `src/celery_app.py`: Celery application configuration
- `data/`: Directory for storing the SQLite database and downloaded files
- `logs/`: Directory for log files
- `start_all.py`: Python script to start all application components
- `start_all.bat`: Windows batch script to start all components
- `start_all.sh`: Unix shell script to start all components

## Adding New Data Sources

To add a new data source:
1. Create a new scraper module in `src/scrapers/`
2. Implement the scraping logic following the existing pattern
3. Create a corresponding Celery task in `src/tasks/scraper_tasks.py`
4. Register the new scraper in the scheduler configuration

## Dependencies

- beautifulsoup4==4.12.2: HTML parsing for web scraping
- requests==2.31.0: HTTP requests
- pandas==2.1.1: Data manipulation
- flask==2.3.3: Web dashboard
- sqlalchemy==2.0.21: Database ORM
- apscheduler==3.10.4: Task scheduling
- python-dotenv==1.0.0: Environment variable management
- selenium==4.15.2: Browser automation for complex scraping
- webdriver-manager==4.0.1: Selenium webdriver management
- celery==5.3.4: Distributed task queue
- redis==5.0.1: Message broker for Celery
- flower==2.0.1: Monitoring tool for Celery

## License

Proprietary - JPS 
## Scraper Health Checks

The application includes an automated health check system that verifies each scraper's functionality. This helps you monitor the status of your data sources and quickly identify any issues.

### Features

- **Automated Checks**: Health checks run automatically every 10 minutes
- **Status Display**: Each data source displays its current status (Working/Not Working/Unknown) on the Data Sources page
- **Manual Checks**: You can manually trigger health checks for individual scrapers or all scrapers at once
- **Diagnostic Information**: Health checks provide error messages and response times to help diagnose issues
- **Asynchronous Processing**: Health checks now run asynchronously using Celery tasks

### How It Works

The health check system performs lightweight tests that verify each scraper can:
1. Connect to its target website
2. Navigate to the correct page
3. Find the expected data elements

This provides early warning if a website changes its structure or becomes unavailable, allowing you to address issues before they impact your data collection.
