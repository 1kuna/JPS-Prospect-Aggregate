# JPS Prospect Aggregate

JPS Prospect Aggregate collects U.S. government procurement forecasts and surfaces them through a Flask API and a React dashboard. Playwright-driven scrapers pull data from agency websites and store the results in a SQLite database via SQLAlchemy (other backends can be configured). Helper scripts populate the database, run scrapers and optionally enhance prospect records using `qwen3` via Ollama.

## Repository Layout

```
app/              Flask application, API routes and scrapers
frontend-react/   React (Vite + TypeScript) dashboard
scripts/          Command line utilities and helpers
migrations/       Alembic migration scripts
tests/            Pytest based unit tests
```

Additional design notes are located in `docs/`.

## Current Features

- Playwright-based scrapers collect forecasts from several federal agencies
- SQLite database managed via SQLAlchemy (other back ends can be configured)
- Flask API exposing prospects, data sources and scraper operations
- React dashboard for browsing and deduplicating opportunities
- Duplicate detection and review workflow
- Optional LLM enrichment of contract values and contacts
- Centralized logging using Loguru
- Script for basic scraper health checks
- Database migrations handled with Alembic
- Helper scripts for running scrapers and LLM enrichment
- Real-time maintenance mode for emergency site disabling

## Setup

1. Activate your conda environment (Python 3.11 recommended):
   ```bash
   conda activate your_environment_name
   ```
   Or create a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install backend dependencies and Playwright browsers:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
3. Copy `.env.example` to `.env` and adjust settings if needed
4. Initialize database (complete setup including user database):
   ```bash
   python scripts/setup_databases.py
   ```
   Or manually:
   ```bash
   alembic upgrade head
   python scripts/populate_data_sources.py
   python scripts/init_user_database.py
   ```
5. Install frontend dependencies:
   ```bash
   cd frontend-react && npm install && cd ..
   ```

## Running

Start the Flask API using Waitress:
```bash
python run.py
```

The React application can be launched separately:
```bash
cd frontend-react
npm run dev  # Includes automatic CSS watching with concurrently
```

Scrapers are run via helper scripts:
```bash
# Run all scrapers
python scripts/run_all_scrapers.py

# Run specific scraper
python -m scripts.run_scraper --source "DHS"

# Test scrapers
python run_scraper_tests.py  # Test all with web server
python test_scraper_individual.py --scraper dhs  # Test individual
```

LLM based enrichment requires Ollama with qwen3 model:
```bash
# Install Ollama from https://ollama.ai/
ollama pull qwen3:latest

# Run enhancement
python scripts/enrichment/enhance_prospects_with_llm.py values --limit 100

# Check LLM status
python scripts/enrichment/enhance_prospects_with_llm.py --check-status
```

## Testing

Execute all unit tests with coverage:
```bash
python -m pytest  # Basic test run
python -m pytest -v --cov=app --cov-report=html  # With coverage report
python -m pytest tests/test_specific.py::test_function -v  # Single test
```

Frontend tests:
```bash
cd frontend-react
npm run test  # Run tests
npm run test:ui  # Run with UI
npm run test:coverage  # Generate coverage report
```

## Current Data Sources

The following agencies are configured through `populate_data_sources.py`:
- [Acquisition Gateway](https://acquisitiongateway.gov/forecast)
- [Social Security Administration](https://www.ssa.gov/oag/business/forecast.html)
- [Department of Commerce](https://www.commerce.gov/oam/industry/procurement-forecasts)
- [Department of Health and Human Services](https://osdbu.hhs.gov/industry/opportunity-forecast)
- [Department of Homeland Security](https://apfs-cloud.dhs.gov/forecast)
- [Department of Justice](https://www.justice.gov/jmd/doj-forecast-contracting-opportunities)
- [Department of Labor](https://acquisitiongateway.gov/forecast)
- [Department of State](https://www.state.gov/procurement-forecast)
- [Department of the Interior](https://acquisitiongateway.gov/forecast)
- [Department of the Treasury](https://osdbu.forecast.treasury.gov)
- [Department of Transportation](https://www.transportation.gov/osdbu/procurement-assistance/summary-forecast)
- [Department of Veterans Affairs](https://acquisitiongateway.gov/forecast)
- [General Services Administration](https://acquisitiongateway.gov/forecast)
- [Nuclear Regulatory Commission](https://acquisitiongateway.gov/forecast)

See `docs/CONTRACT_MAPPING_LLM.md` for LLM implementation details. The scraper architecture uses a unified `ConsolidatedScraperBase` class (see inline documentation in `app/core/consolidated_scraper_base.py`).

## Data Retention

A built-in utility manages raw data file storage with a rolling cleanup policy that prevents storage bloat by keeping only the most recent files per data source.

**Current Impact**: Reduces storage from 86 files (84MB) to 43 files (~42MB) - **50% reduction**

### Usage
```bash
# Preview what would be deleted (safe mode - keeps 3 most recent files per source)
python app/utils/data_retention.py

# Actually delete files
python app/utils/data_retention.py --execute

# Custom retention count
python app/utils/data_retention.py --execute --retention-count 5
```

The utility scans `data/raw/` directories, parses timestamps from filenames (`prefix_YYYYMMDD_HHMMSS.ext`), sorts by newest first, and deletes older files beyond the retention limit. It includes safety features like dry-run mode by default, detailed logging, and error handling for invalid timestamps.

## Maintenance Mode

The system includes a real-time maintenance mode that can instantly disable the entire site during emergencies or critical issues. This is particularly useful in Docker deployments where you need immediate control without container restarts.

### Features
- **Real-time toggling** - Enable/disable instantly without restarts
- **Database-persisted** - Survives deployments and container restarts  
- **Admin access preserved** - Admin endpoints remain accessible during maintenance
- **Clean user experience** - Shows professional maintenance page (HTTP 503)

### Usage

**Enable maintenance mode:**
```bash
curl -X POST http://localhost:5000/api/admin/maintenance \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

**Disable maintenance mode:**
```bash
curl -X POST http://localhost:5000/api/admin/maintenance \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

**Check current status:**
```bash
curl http://localhost:5000/api/admin/maintenance
```

**Health check (works during maintenance):**
```bash
curl http://localhost:5000/api/admin/health
```

When enabled, all user-facing endpoints return a maintenance page while admin endpoints remain functional for system management.

## Upcoming Features

- Automated refresh schedule to keep data sources up to date
- Background task queue for scrapers and enrichment
- Expanded logging configuration
- Faster and more efficient processing pipeline
- Scraper health alerts with notifications
- Go/no-go tagging with user attribution
- Scrape with specific parameters for sites with limited extraction like ACQG
