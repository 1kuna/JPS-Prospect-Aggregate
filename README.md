# JPS Proposal Forecast Aggregator

A dashboard application that scrapes data from various government proposal forecast sites and organizes them into a searchable, sortable dashboard.

## Features

- Automated scraping of proposal forecast data from government websites
- Data storage in a structured SQLite database (configurable for other databases)
- Web-based dashboard for viewing and analyzing proposal opportunities
- Filtering and sorting capabilities by various criteria
- Scheduled data refresh to keep information current
- Asynchronous task processing with Celery for improved performance
- Health monitoring of scrapers with automated alerts
- Docker support for easy deployment

## Current Data Sources

- [Acquisition Gateway Forecast](https://acquisitiongateway.gov/forecast)
- [SSA Contract Forecast](https://www.ssa.gov/oag/business/forecast.html)

## Project Structure

```
.
├── app.py                  # Main application entry point
├── src/                    # Source code directory
│   ├── dashboard/          # Flask web application
│   │   ├── app.py          # Flask app factory
│   │   ├── blueprints/     # Route definitions
│   │   ├── static/         # Static assets (CSS, JS)
│   │   └── templates/      # HTML templates
│   ├── scrapers/           # Web scraper implementations
│   │   ├── base_scraper.py # Base scraper class
│   │   └── ...             # Specific scraper implementations
│   ├── database/           # Database models and operations
│   ├── tasks/              # Celery background tasks
│   └── utils/              # Utility functions
├── data/                   # Data storage directory
│   └── downloads/          # Downloaded files from scrapers
├── logs/                   # Application logs
├── scripts/                # Utility scripts
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
└── docker-compose.yml      # Docker Compose configuration
```

## Setup Instructions

### Local Development Setup

#### Prerequisites

- Python 3.9+
- Redis (for Celery task queue)
- Git

#### Installation

1. Clone this repository
   ```bash
   git clone https://github.com/yourusername/JPS-Prospect-Aggregate.git
   cd JPS-Prospect-Aggregate
   ```

2. Create and activate a Conda environment
   ```bash
   # Create a new Conda environment
   conda create -n jps_env python=3.10
   
   # Activate the environment
   # On Windows
   conda activate jps_env
   
   # On macOS/Linux
   conda activate jps_env
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers
   ```bash
   playwright install
   ```

5. Create a `.env` file based on `.env.example`
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. Initialize the database
   ```bash
   python create_tables.py
   ```

### Docker Setup (Recommended for Production)

1. Clone this repository
   ```bash
   git clone https://github.com/yourusername/JPS-Prospect-Aggregate.git
   cd JPS-Prospect-Aggregate
   ```

2. Create a `.env` file based on `.env.example`
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Build and start the Docker containers
   ```bash
   docker-compose up -d
   ```

4. Access the application at http://localhost:5001
   
5. Access Flower (Celery monitoring) at http://localhost:5555

## Running the Application

### Local Development

1. Start Redis (required for Celery)
   ```bash
   # Install Redis if not already installed
   # On Windows, you can use Redis for Windows or WSL
   # On macOS: brew install redis && brew services start redis
   # On Linux: sudo apt install redis-server && sudo systemctl start redis
   ```

2. Start the Flask application
   ```bash
   python app.py
   ```

3. In a separate terminal, start the Celery worker
   ```bash
   celery -A src.celery_app.celery_app worker --loglevel=info
   ```

4. In another terminal, start the Celery beat scheduler
   ```bash
   celery -A src.celery_app.celery_app beat --loglevel=info
   ```

5. (Optional) Start Flower for monitoring Celery tasks
   ```bash
   celery -A src.celery_app.celery_app flower
   ```

### Using Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Configuration

The application is configured using environment variables, which can be set in the `.env` file:

- `FLASK_ENV`: Set to `development`, `production`, or `testing` (default: `development`)
- `DEBUG`: Enable debug mode (`true` or `false`, default: `false`)
- `HOST`: Host to bind the Flask application (default: `0.0.0.0`)
- `PORT`: Port to bind the Flask application (default: `5001`)
- `DATABASE_URL`: Database connection URL (default: SQLite database in the data directory)
- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `SCRAPE_INTERVAL_HOURS`: How often to run scrapers (default: `24`)
- `HEALTH_CHECK_INTERVAL_MINUTES`: How often to check scraper health (default: `10`)

See `.env.example` for a complete list of configuration options.

## Adding a New Scraper

1. Create a new scraper class in `src/scrapers/` that inherits from `BaseScraper`
2. Implement the required methods: `scrape()`, `parse()`, and `save()`
3. Register the scraper in `src/scrapers/__init__.py`
4. Add a new Celery task in `src/tasks/scraper_tasks.py`
5. Add the task to the beat schedule in `src/celery_app.py`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Documentation

Additional documentation is available in the `docs` folder:

- [Celery Documentation](docs/CELERY_README.md) - Detailed information about Celery setup and configuration
- [Vue.js Frontend Documentation](docs/VUE_README.md) - Information about the Vue.js frontend

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
