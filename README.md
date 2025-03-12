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

## Current Data Sources

- [Acquisition Gateway Forecast](https://acquisitiongateway.gov/forecast)
- [SSA Contract Forecast](https://www.ssa.gov/oag/business/forecast.html)

## Project Structure

```
.
├── server.py                  # Main backend application entry point
├── start_all.py               # Script to start all services
├── src/                       # Backend source code directory
│   ├── dashboard/             # Flask web application
│   │   ├── factory.py         # Flask app factory
│   │   ├── blueprints/        # Route definitions
│   │   ├── static/            # Static assets (CSS, JS)
│   │   └── templates/         # HTML templates
│   ├── scrapers/              # Web scraper implementations
│   │   ├── base_scraper.py    # Base scraper class
│   │   └── ...                # Specific scraper implementations
│   ├── database/              # Database models and operations
│   ├── tasks/                 # Celery background tasks
│   ├── utils/                 # Utility functions
│   ├── config.py              # Configuration settings
│   ├── celery_app.py          # Celery configuration
│   └── exceptions.py          # Custom exceptions
├── frontend-react/            # React frontend application
│   ├── src/                   # React source code
│   │   ├── assets/            # Images, fonts, etc.
│   │   ├── components/        # Reusable components
│   │   │   └── ui/            # shadcn/ui components
│   │   ├── context/           # React context providers
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # Utility functions
│   │   ├── pages/             # Page components
│   │   ├── store/             # Zustand store
│   │   ├── utils/             # Utility functions
│   │   ├── App.tsx            # Main application component
│   │   ├── main.tsx           # Application entry point
│   │   └── index.css          # Global styles
│   ├── public/                # Public assets
│   ├── package.json           # Frontend dependencies
│   └── vite.config.ts         # Vite configuration
├── data/                      # Data storage directory
│   └── downloads/             # Downloaded files from scrapers
├── logs/                      # Application logs
├── scripts/                   # Utility scripts
├── docs/                      # Documentation
├── requirements.txt           # Python dependencies
├── .env.example               # Example environment configuration
└── .env                       # Environment configuration (not in version control)
```

## Setup Instructions

### Local Development Setup

#### Prerequisites

- Python 3.9+
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
python start_all.py
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
   python rebuild_frontend.py
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

See `.env.example` for a complete list of configuration options.

## Adding a New Scraper

1. Create a new scraper class in `src/scrapers/` that inherits from `BaseScraper`
2. Implement the required methods: `scrape()`, `parse()`, and `save()`
3. Register the scraper in `src/scrapers/__init__.py`
4. Add a new Celery task in `src/tasks/scraper_tasks.py`
5. Add the task to the beat schedule in `src/celery_app.py`

## Testing

The project includes several test scripts to verify functionality:

```bash
# Test scraper status
python test_scraper_status.py

# Test health check functionality
python test_health_check.py

# Check proposals in the database
python check_proposals.py
```

## Scraper Health Checks

The application includes an automated health check system that verifies each scraper's functionality. This helps you monitor the status of your data sources and quickly identify any issues.

### Features

- **Automated Checks**: Health checks run automatically every 10 minutes
- **Status Display**: Each data source displays its current status (Working/Not Working/Unknown) on the Data Sources page
- **Manual Checks**: You can manually trigger health checks for individual scrapers or all scrapers at once
- **Diagnostic Information**: Health checks provide error messages and response times to help diagnose issues
- **Asynchronous Processing**: Health checks run asynchronously using Celery tasks

### How It Works

The health check system performs lightweight tests that verify each scraper can:
1. Connect to its target website
2. Navigate to the correct page
3. Find the expected data elements

This provides early warning if a website changes its structure or becomes unavailable, allowing you to address issues before they impact your data collection.

## Architecture

### Backend Architecture

The backend uses the following components:

- **Flask**: Web application framework for the API
- **SQLAlchemy**: ORM for database access
- **Celery**: Task queue for asynchronous and scheduled tasks
- **Redis**: Message broker and result backend for Celery
- **Playwright**: Browser automation for web scraping

### Frontend Architecture

The frontend is built with:

- **React**: JavaScript library for building user interfaces
- **TypeScript**: Typed superset of JavaScript
- **Vite**: Next-generation frontend tooling
- **shadcn/ui**: Beautifully designed components built with Radix UI and Tailwind CSS
- **TanStack Table**: Headless UI for building powerful tables
- **Zustand**: State management solution
- **React Router**: Declarative routing for React
- **React Hook Form**: Performant, flexible and extensible forms
- **Zod**: TypeScript-first schema validation
- **Tailwind CSS**: Utility-first CSS framework

## Troubleshooting

### Redis Connection Issues

If you encounter Redis connection issues, make sure Redis is running:

```bash
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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
