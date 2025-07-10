# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

1. Activate your conda environment (Python 3.11 recommended):
   ```bash
   conda activate your_environment_name
   ```
2. Install dependencies and browsers:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
3. Copy `.env.example` to `.env` and adjust settings if needed
4. Initialize database:
   ```bash
   # Complete database setup (includes all initialization steps)
   python scripts/setup_databases.py
   ```
5. Install frontend dependencies:
   ```bash
   cd frontend-react && npm install && cd ..
   ```

## Commands

### Backend Development
```bash
# Start development server (Waitress + Flask)
python run.py

# Run all scrapers
python scripts/run_all_scrapers.py

# Run specific scraper
python -m scripts.run_scraper --source "DHS"

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Run tests with coverage (configuration in pytest.ini)
python -m pytest

# Run single test
python -m pytest tests/test_specific.py::test_function -v

# LLM enhancement (requires Ollama with qwen3 model)
python scripts/enrichment/enhance_prospects_with_llm.py values --limit 100

# Check LLM status
python scripts/enrichment/enhance_prospects_with_llm.py --check-status
```

### Scraper Testing
```bash
# Test all scrapers
python run_scraper_tests.py

# Test specific scraper
python run_scraper_tests.py --scraper dhs

# Test individual scraper without web server
python test_scraper_individual.py --scraper acquisition_gateway

# Test all scrapers individually
python test_scraper_individual.py --scraper all

# List available scrapers
python test_scraper_individual.py --list
```

### Decision System & ML Export
```bash
# Export decisions for LLM training
python scripts/export_decisions_for_llm.py --format jsonl

# Export only decisions with reasoning
python scripts/export_decisions_for_llm.py --reasons-only

# Export to both JSONL and CSV
python scripts/export_decisions_for_llm.py --format both
```

### Frontend Development
```bash
cd frontend-react

# Development with CSS watching (uses concurrently)
npm run dev

# Build for production
npm run build

# Lint TypeScript
npm run lint

# Preview production build
npm run preview

# Run tests
npm run test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

### Maintenance
```bash
# Data retention cleanup (preview mode by default)
python app/utils/data_retention.py

# Execute cleanup (keeps 3 most recent files per source)
python app/utils/data_retention.py --execute

# Custom retention count
python app/utils/data_retention.py --execute --retention-count 5

# Database health check
python -m scripts.health_check

# Export data to CSV
python -m scripts.export_csv

# Data validation
python scripts/validate_file_naming.py
```

## Prerequisites

**LLM Requirements:**
- Install Ollama from https://ollama.ai/
- Required model: `ollama pull qwen3:latest`

**Environment Configuration:**
- Separate database URLs for business and user data (security isolation)
- Playwright timeouts configurable via environment variables
- File processing settings: `FILE_FRESHNESS_SECONDS`

## Debugging

**Error Handling:**
- Screenshots saved to: `logs/error_screenshots/`
- HTML dumps saved to: `logs/error_html/`
- Logs: `logs/app.log`, `logs/scrapers.log`, `logs/errors.log`

## Architecture

### Scraper Framework
The scraper system uses a unified architecture for efficient web scraping:

- **ConsolidatedScraperBase** (`app/core/consolidated_scraper_base.py`): Unified base class containing all scraping functionality (browser automation, navigation, downloads, data processing)
- **ScraperConfig**: Single configuration dataclass for all scraper settings
- **Config Converter** (`app/core/config_converter.py`): Functions to create configurations for each agency scraper
- **Agency Scrapers** (`app/core/scrapers/`): Simple implementations focusing only on agency-specific logic (each ~50-100 lines)

Key features:
- Unified configuration system
- Built-in error handling with screenshots and HTML dumps
- Stealth mode for avoiding detection
- Automatic retry logic
- Structured data processing pipeline

### Creating New Scrapers
```python
from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.config_converter import create_your_agency_config

class YourAgencyScraper(ConsolidatedScraperBase):
    def __init__(self):
        config = create_your_agency_config()
        config.base_url = active_config.YOUR_AGENCY_URL
        super().__init__(config)
    
    # Add custom transformations if needed
    def custom_transform(self, df):
        return df
```

### Database Layer
- **Models** (`app/database/models.py`): SQLAlchemy models for prospects, data sources, scraper status
- **Operations** (`app/database/operations.py`): High-level database operations with duplicate detection and bulk operations
- **Migrations** (`migrations/`): Alembic-managed schema changes
- **User Authentication**: Separate user database for security isolation
- **Decision Tracking**: Go/no-go decisions linked to users and prospects

### API Layer
Flask app with modular blueprints:
- **Main API** (`app/api/`): RESTful endpoints for prospects, data sources, duplicates
- **Decision API** (`/api/decisions/`): CRUD operations for go/no-go decisions
- **Health endpoints**: Database connectivity and system status
- **Pagination support**: Efficient large dataset handling

Key decision endpoints:
- `POST /api/decisions/` - Create/update decision
- `GET /api/decisions/<prospect_id>` - Get decisions for prospect
- `GET /api/decisions/my` - Get current user's decisions
- `DELETE /api/decisions/<id>` - Delete a decision

### Frontend Architecture
React TypeScript application with:
- **TanStack Table**: Virtualized tables for performance with large datasets
- **TanStack Query**: API state management and caching
- **Tailwind + Radix UI**: Component system and styling
- **Type-safe API integration**: Full TypeScript coverage for API responses

### Data Processing Pipeline
1. **Scraping**: Agency-specific scrapers collect raw data using configuration-driven processing
2. **Duplicate Detection**: Fuzzy matching with confidence scoring in `app/services/duplicate_detection.py`
3. **LLM Enhancement**: AI processing for value extraction, contact parsing, and title improvement using qwen3 via Ollama
4. **Data Retention**: Automated cleanup preserving recent data while managing storage

### Key Patterns

**Configuration-Driven Development**: Each scraper uses dataclass configurations defining:
- Field mappings from raw data to database schema
- Data processing rules (value parsing, date formatting)
- Download behavior and file handling
- Duplicate detection criteria

**Unified Architecture**: Scrapers inherit from a single base class with unified configuration:
```python
class AgencyScraper(ConsolidatedScraperBase):
    def __init__(self):
        config = create_agency_config()
        super().__init__(config)
```

**Error Handling Strategy**: All scrapers capture screenshots and HTML dumps on failure, with structured logging via Loguru for debugging.

**Performance Optimizations**:
- N+1 query prevention in duplicate detection
- Table virtualization in frontend for large datasets  
- Bulk database operations for imports
- Efficient pagination with SQLAlchemy

### LLM Integration
The system uses Ollama with qwen3 model for data enhancement:
- **Value Parsing**: Extract contract values from unstructured text
- **Contact Extraction**: Parse emails and contact names
- **Title Enhancement**: Improve prospect titles for clarity
- **NAICS Classification**: Automatic categorization

LLM services are in `app/services/llm_service.py` with comprehensive logging and error handling.

### Testing Strategy
- **Unit Tests**: Individual component testing
- **Integration Tests**: Database and API endpoint testing
- **Scraper Tests**: Mock-based testing for web scraping components
- **Coverage Reporting**: HTML reports for test coverage analysis

Run `python -m pytest tests/ -v --cov=app --cov-report=html` for full test suite with coverage.

## Data Sources

System currently scrapes 9 federal agencies:

- Acquisition Gateway, Social Security Administration, Department of Commerce
- Health and Human Services, Homeland Security, Justice  
- State, Treasury, Transportation

## Data Retention

Built-in utility manages storage with rolling cleanup policy:

- **Current Impact**: 50% storage reduction (86 files/84MB → 43 files/42MB)
- **Default**: Keeps 3 most recent files per data source
- **Safety**: Dry-run mode by default with detailed logging

