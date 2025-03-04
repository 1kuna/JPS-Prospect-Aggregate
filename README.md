# JPS Proposal Forecast Aggregator

A dashboard application that scrapes data from various proposal forecast sites and organizes them into a searchable, sortable dashboard.

## Features

- Automated scraping of proposal forecast data from government websites
- Data storage in a structured SQLite database
- Web-based dashboard for viewing and analyzing proposal opportunities
- Filtering and sorting capabilities by various criteria
- Scheduled data refresh to keep information current

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
   python init_db.py
   ```
7. Run the application:
   ```
   python app.py
   ```

## Running Components Individually

- Run the web scraper: `python run_scraper.py`
- Run the scheduler: `python run_scheduler.py`

## Project Structure

- `app.py`: Main application entry point for the Flask dashboard
- `init_db.py`: Script to initialize the database
- `run_scraper.py`: Script to run the scraper manually
- `run_scheduler.py`: Script to start the scheduler
- `src/scrapers/`: Web scraping modules for different data sources
- `src/database/`: Database models and connection management
- `src/dashboard/`: Flask web application for the dashboard
- `src/scheduler/`: Scheduled tasks for data refresh
- `data/`: Directory for storing the SQLite database

## Adding New Data Sources

To add a new data source:
1. Create a new scraper module in `src/scrapers/`
2. Implement the scraping logic following the existing pattern
3. Register the new scraper in the scheduler

## Dependencies

- beautifulsoup4: HTML parsing for web scraping
- requests: HTTP requests
- pandas: Data manipulation
- flask: Web dashboard
- sqlalchemy: Database ORM
- apscheduler: Task scheduling
- selenium: Browser automation for complex scraping
- webdriver-manager: Selenium webdriver management

## License

Proprietary - JPS 