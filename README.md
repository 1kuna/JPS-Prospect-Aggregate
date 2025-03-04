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
   python src/database/init_db.py
   ```
7. Run the application:
   ```
   python app.py
   ```

## Database Management

The project includes several scripts for database management:

- `create_new_db.py`: Creates a new database with the current schema
- `rebuild_db.py`: Rebuilds the database while preserving existing data
- `import_csv.py`: Imports data from CSV files in the downloads directory
- `process_csv.py`: Rebuilds the database and processes CSV files

## Project Structure

- `app.py`: Main application entry point for the Flask dashboard
- `src/database/init_db.py`: Script to initialize the database
- `src/scrapers/`: Web scraping modules for different data sources
  - `acquisition_gateway.py`: Scraper for Acquisition Gateway Forecast
  - `ssa_contract_forecast.py`: Scraper for SSA Contract Forecast
- `src/database/`: Database models and connection management
- `src/dashboard/`: Flask web application for the dashboard
- `src/scheduler/`: Scheduled tasks for data refresh
- `data/`: Directory for storing the SQLite database and downloaded files
- `logs/`: Directory for log files

## Adding New Data Sources

To add a new data source:
1. Create a new scraper module in `src/scrapers/`
2. Implement the scraping logic following the existing pattern
3. Register the new scraper in the scheduler (`src/scheduler/scheduler.py`)

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

## License

Proprietary - JPS 