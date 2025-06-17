# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

1. Create and activate Python virtual environment (Python 3.11 recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies and browsers:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
3. Copy `.env.example` to `.env` and adjust settings if needed
4. Initialize database:
   ```bash
   flask db upgrade
   python scripts/populate_data_sources.py
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

# Run tests with coverage
python -m pytest tests/ -v --cov=app --cov-report=html

# Run single test
python -m pytest tests/test_specific.py::test_function -v

# LLM enhancement (requires Ollama)
python scripts/enrichment/enhance_prospects_with_llm.py values --limit 100
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
```

## Architecture

### Scraper Framework
The scraper system is built on a composable architecture:

- **BaseScraper** (`app/core/base_scraper.py`): Core scraping functionality with error handling, screenshots on failure, and structured logging
- **Mixins** (`app/core/mixins/`): Reusable components for navigation, downloading, and data processing that compose into scrapers
- **Agency Scrapers** (`app/core/scrapers/`): Specific implementations for each government agency (DoD, DHS, DOJ, etc.)
- **Configurations** (`app/core/configs/`): Dataclass-based configs defining data processing rules, field mappings, and scraper behavior

Each scraper inherits from BaseScraper and composes mixins based on needs. Configuration classes define how raw data is processed, what fields to extract, and how to handle duplicates.

### Database Layer
- **Models** (`app/database/models.py`): SQLAlchemy models for prospects, data sources, scraper status
- **Operations** (`app/database/operations.py`): High-level database operations with duplicate detection and bulk operations
- **Migrations** (`migrations/`): Alembic-managed schema changes

### API Layer
Flask app with modular blueprints:
- **Main API** (`app/api/`): RESTful endpoints for prospects, data sources, duplicates
- **Health endpoints**: Database connectivity and system status
- **Pagination support**: Efficient large dataset handling

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

**Mixin Composition**: Scrapers compose functionality from mixins rather than inheritance:
```python
class AgencyScraper(BaseScraper, NavigationMixin, DownloadMixin, DataProcessingMixin):
    def __init__(self):
        super().__init__(config=AgencyConfig())
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

System currently scrapes 14+ federal agencies including:

- Acquisition Gateway, Social Security Administration, Department of Commerce
- Health and Human Services, Homeland Security, Justice
- Labor, State, Interior, Treasury, Transportation, Veterans Affairs
- General Services Administration, Nuclear Regulatory Commission

## Data Retention

Built-in utility manages storage with rolling cleanup policy:

- **Current Impact**: 50% storage reduction (86 files/84MB → 43 files/42MB)
- **Default**: Keeps 3 most recent files per data source
- **Safety**: Dry-run mode by default with detailed logging