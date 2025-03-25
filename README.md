# JPS Proposal Forecast Aggregator

A dashboard application that scrapes data from various government proposal forecast sites and organizes them into a searchable, sortable dashboard.

## Features

- Automated scraping of proposal forecast data from government websites
- Data storage in a structured SQLite database (configurable for other databases)
- Modern React frontend with TypeScript and Tailwind CSS
- Web-based dashboard for viewing and analyzing proposal opportunities
- Filtering and sorting capabilities by various criteria
- Scheduled data refresh to keep information current
- Asynchronous task processing with Celery for improved performance
- Health monitoring of scrapers with automated alerts
- Robust logging with Loguru
- Type checking with MyPy
- Code formatting with Black
- Data validation with Pydantic

## Current Data Sources

- [Acquisition Gateway Forecast](https://acquisitiongateway.gov/forecast)
- [SSA Contract Forecast](https://www.ssa.gov/oag/business/forecast.html)

## Project Structure

```
.
├── server.py                  # Main backend application entry point
├── run_app.py                # Application runner with additional utilities
├── src/                      # Backend source code directory
│   ├── dashboard/            # Flask web application
│   │   ├── factory.py        # Flask app factory
│   │   ├── blueprints/       # Route definitions
│   │   ├── static/          # Static assets (CSS, JS)
│   │   └── templates/       # HTML templates
│   ├── scrapers/            # Web scraper implementations
│   │   ├── base_scraper.py  # Base scraper class
│   │   └── ...             # Specific scraper implementations
│   ├── database/           # Database models and operations
│   ├── tasks/              # Celery background tasks
│   ├── utils/              # Utility functions
│   ├── config.py           # Configuration settings
│   ├── celery_app.py       # Celery configuration
│   └── exceptions.py       # Custom exceptions
├── frontend-react/         # React frontend application
│   ├── src/               # React source code
│   │   ├── assets/       # Images, fonts, etc.
│   │   ├── components/   # Reusable components
│   │   │   └── ui/      # shadcn/ui components
│   │   ├── context/     # React context providers
│   │   ├── hooks/       # Custom React hooks
│   │   ├── lib/         # Utility functions
│   │   ├── pages/       # Page components
│   │   ├── store/       # Zustand store
│   │   ├── utils/       # Utility functions
│   │   ├── App.tsx      # Main application component
│   │   ├── main.tsx     # Application entry point
│   │   └── index.css    # Global styles
│   ├── public/          # Public assets
│   ├── package.json     # Frontend dependencies
│   └── vite.config.ts   # Vite configuration
├── data/                # Data storage directory
│   └── downloads/       # Downloaded files from scrapers
├── logs/               # Application logs
├── scripts/            # Utility scripts
├── docs/               # Documentation
├── tests/              # Test suite
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment configuration
└── .env               # Environment configuration (not in version control)
```

## Setup Instructions

### Local Development Setup

#### Prerequisites

- Python 3.10+
- Node.js 18+ and npm/yarn
- Redis (for Celery task queue)
- Git

#### Backend Installation

1. Clone this repository
   ```bash
   git clone https://github.com/yourusername/JPS-Prospect-Aggregate.git
   cd JPS-Prospect-Aggregate
   ```

2. Create and activate a virtual environment
   ```bash
   # Using venv
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   
   # Or using Conda
   conda create -n jps_env python=3.10
   conda activate jps_env
   ```

3. Install backend dependencies
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

#### Frontend Installation

1. Navigate to the frontend directory
   ```bash
   cd frontend-react
   ```

2. Install frontend dependencies
   ```bash
   npm install
   # or
   yarn install
   ```

## Running the Application

### Running All Services

The easiest way to run all services is to use the provided script:

```bash
python run_app.py
```

This script will start the Flask backend, Celery worker, Celery beat scheduler, and React development server.

### Running Services Individually

#### Backend

1. Start Redis (required for Celery)
   ```bash
   # Install Redis if not already installed
   # On Windows, you can use Redis for Windows or WSL
   # On macOS: brew install redis && brew services start redis
   # On Linux: sudo apt install redis-server && sudo systemctl start redis
   ```

2. Start the Flask application
   ```bash
   python server.py
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

#### Frontend

1. Navigate to the frontend directory
   ```bash
   cd frontend-react
   ```

2. Start the development server
   ```bash
   npm run dev
   # or
   yarn dev
   ```

3. Access the application at http://localhost:5173

### Building for Production

1. Build the frontend
   ```bash
   cd frontend-react
   npm run build
   # or
   yarn build
   ```

2. The built frontend will be available in `frontend-react/dist`

3. You can use the `rebuild_frontend.py` script to automatically build and copy the frontend to the correct location:
   ```bash
   python scripts/rebuild_frontend.py
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
- `CELERY_BROKER_URL`: Celery broker URL (default: `redis://localhost:6379/0`)
- `CELERY_RESULT_BACKEND`: Celery result backend URL (default: `redis://localhost:6379/0`)
- `SQL_ECHO`: Enable SQL query logging (default: `False`)
- `LOG_LEVEL`: Set logging level (default: `INFO`)

See `.env.example` for a complete list of configuration options.

## Development

### Code Quality Tools

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **MyPy**: Static type checking
- **Pytest**: Testing framework
- **Pydantic**: Data validation
- **Loguru**: Enhanced logging

### Adding a New Scraper

1. Create a new scraper class in `src/scrapers/` that inherits from `BaseScraper`
2. Implement the required methods: `scrape()`, `parse()`, and `save()`
3. Register the scraper in `src/scrapers/__init__.py`
4. Add a new Celery task in `src/tasks/scraper_tasks.py`
5. Add the task to the beat schedule in `src/celery_app.py`

### Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_scrapers.py
```

## Monitoring

- **Celery Flower**: Monitor Celery tasks at http://localhost:5555
- **Application Logs**: Check the `logs/` directory for detailed application logs
- **Health Checks**: Monitor scraper health through the dashboard interface

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure code quality tools pass
5. Submit a pull request

## License

This project is proprietary and confidential. All rights reserved.
