# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

### Option 1: Docker Setup (Recommended for Production)

**Quick Start (Automated):**
```bash
# Use the automated build script
./docker/docker-build.sh
```

This script will:
- Check for .env file and required configurations
- Validate environment settings
- Build and start all services
- Verify services are running correctly

**Manual Setup:**

1. **Copy environment file and configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings:
   # - Set ENVIRONMENT=production
   # - Set SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
   # - Set ENVIRONMENT=production
   ```

2. **Build and start all services:**
   ```bash
   docker-compose up --build -d
   # Or use helper scripts:
   # Unix/Mac: ./docker/docker-start.sh
   # Windows:  ./docker/docker-start.ps1
   ```

3. **Access the application:**
   - Web interface: http://localhost:5001
   - Ollama LLM API: http://localhost:11434

4. **Monitor services:**
   ```bash
   docker-compose ps
   docker-compose logs -f web
   ```

### Option 2: Local Development Setup

1. Activate your conda environment (Python 3.11 recommended):
   ```bash
   conda activate your_environment_name
   ```
2. Install dependencies and browsers:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
3. Copy `.env.example` to `.env` and set ENVIRONMENT=development
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

### Docker Operations
```bash
# Automated build and deploy (recommended)
./docker/docker-build.sh

# Or manual Docker commands:
# Build and start all services
docker-compose up --build -d

# Stop all services
docker-compose down

# View service status
docker-compose ps

# View logs
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f ollama

# Manual backup
docker exec jps-backup /backup.sh

# Access database directly
docker exec -it jps-db psql -U jps_user -d jps_prospects

# Restart specific service
docker-compose restart web

# Clean rebuild (if you have issues)
docker-compose down -v
docker-compose up --build -d

# Use minimal setup (without Ollama)
docker-compose -f docker-compose-minimal.yml up -d
```

**Docker Helper Scripts:**
- `docker/docker-build.sh` - Automated build with environment validation
- `docker/docker-start.sh` - Start services (Unix/Mac)
- `docker/docker-start.ps1` - Start services (Windows PowerShell)
- `docker/deploy.sh` or `deploy.ps1` - Full deployment scripts

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

### CI/CD Quick Reference

#### Local CI Testing (Pre-Push)
```bash
# Run full CI test suite locally (recommended before pushing)
make test-ci

# Run specific test suites
make test-python        # Python tests, linting, type checking
make test-frontend      # Frontend tests, TypeScript, ESLint
make test-integration   # Integration tests only
make test-all          # Everything including E2E tests

# Quick checks
make lint-python       # Just Python linting
make lint-frontend     # Just frontend linting
make type-check-python # Just Python type checking
make type-check-frontend # Just TypeScript checking

# Clean test artifacts
make clean
```

#### CI Pipeline Stages
1. **Parallel Testing** - Python and Frontend tests run concurrently
2. **Integration Testing** - Cross-system tests with SQLite
3. **End-to-End Testing** - Full workflow testing with Playwright
4. **Security Scanning** - Dependency vulnerabilities and code security

#### Common CI Failures and Fixes
```bash
# TypeScript strict mode errors in tests
cd frontend-react && npm test -- --typecheck

# Python version mismatch (CI uses 3.11)
conda create -n jps-py311 python=3.11
conda activate jps-py311
pip install -r requirements.txt

# Missing browser dependencies for E2E
npx playwright install --with-deps

# Database connection issues
docker-compose -f ci-test/docker-compose.test.yml up -d db
```

### Testing Commands

#### Backend Testing
```bash
# Run all backend tests with coverage
python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# Run specific test modules
python -m pytest tests/database/ -v                 # Database tests only
python -m pytest tests/api/ -v                      # API tests only  
python -m pytest tests/core/ -v                     # Core scraper tests
python -m pytest tests/services/ -v                 # Service layer tests
python -m pytest tests/utils/ -v                    # Utility function tests

# Run tests with different verbosity levels
python -m pytest tests/ -v                          # Verbose output
python -m pytest tests/ -vv                         # Extra verbose
python -m pytest tests/ -q                          # Quiet output

# Run tests matching specific patterns
python -m pytest tests/ -k "test_prospect"          # Tests containing "prospect"
python -m pytest tests/ -k "api and not slow"       # API tests excluding slow ones
python -m pytest tests/ -m "not integration"        # Skip integration tests

# Run tests with coverage thresholds
python -m pytest tests/ --cov=app --cov-fail-under=75

# Run tests with performance profiling
python -m pytest tests/ --durations=10              # Show 10 slowest tests

# Run specific test files or functions
python -m pytest tests/api/test_prospects_api.py::test_get_prospects -v
python -m pytest tests/database/test_models.py -v

# Run tests in parallel (requires pytest-xdist)
python -m pytest tests/ -n auto                     # Auto-detect CPU cores
python -m pytest tests/ -n 4                        # Use 4 workers

# Run tests with database setup/teardown
python -m pytest tests/ --setup-show                # Show fixture setup
python -m pytest tests/ --tb=short                  # Short traceback format
python -m pytest tests/ --tb=line                   # Line-only traceback
```

#### Frontend Testing  
```bash
cd frontend-react

# Run all frontend tests
npm run test                                         # Interactive mode
npm run test -- --run                               # Run once and exit
npm run test -- --watch                             # Watch mode (default)

# Run tests with coverage
npm run test:coverage                                # Generate coverage report
npm run test:coverage -- --run                      # Coverage in CI mode

# Run specific test files
npm test -- ProspectTable.test.tsx                  # Single component test
npm test -- --testNamePattern="ProspectTable"       # Tests matching pattern

# Run tests with different reporters
npm test -- --reporter=verbose                      # Detailed output
npm test -- --reporter=basic                        # Minimal output
npm test -- --reporter=json                         # JSON output

# Run tests in UI mode (browser interface)
npm run test:ui                                      # Interactive test UI

# Debug specific tests
npm test -- --no-coverage ProspectTable.test.tsx    # Run without coverage
npm test -- --run --reporter=verbose                # Debug mode
```

#### Integration Testing
```bash
# Run integration tests only
python -m pytest tests/integration/ -v -m integration

# Run LLM integration tests (requires Ollama)
python -m pytest tests/integration/test_llm_api_integration.py -v

# Run API integration tests
python -m pytest tests/api/ -v --integration
```

#### End-to-End Testing
```bash
cd frontend-react

# Install Playwright browsers (first time setup)
npx playwright install

# Run all E2E tests
npx playwright test

# Run E2E tests in headed mode (see browser)
npx playwright test --headed

# Run specific E2E test files
npx playwright test prospect-management.spec.ts

# Run E2E tests with debugging
npx playwright test --debug                         # Step through tests
npx playwright test --trace on                      # Generate traces

# Generate test report
npx playwright show-report
```

#### Test Utilities and Debugging
```bash
# Pre-commit testing (runs automatically before commits)
pre-commit run --all-files                          # Run all pre-commit hooks
pre-commit run pytest-check                         # Run only pytest hook
pre-commit run vitest-check                         # Run only frontend tests

# Security testing
bandit -r app/ -f json                              # Python security scan
npm audit --audit-level moderate                    # Frontend dependency audit
safety check                                        # Check Python dependencies

# Performance testing
python -m pytest tests/ --benchmark-only            # Run benchmark tests only
python -m pytest tests/ --benchmark-skip            # Skip benchmark tests

# Test data management
python scripts/setup_test_data.py                   # Create test fixtures
python scripts/cleanup_test_data.py                 # Clean test database
```

#### Coverage Analysis
```bash
# Generate detailed coverage reports
python -m pytest tests/ --cov=app --cov-report=html --cov-report=xml
cd frontend-react && npm run test:coverage -- --run

# View coverage reports
open htmlcov/index.html                             # Python coverage report
open frontend-react/coverage/index.html             # Frontend coverage report

# Coverage with missing lines
python -m pytest tests/ --cov=app --cov-report=term-missing

# Fail build if coverage drops below threshold
python -m pytest tests/ --cov=app --cov-fail-under=75
cd frontend-react && npm run test:coverage -- --run --coverage.thresholds.statements=80
```

### Maintenance
```bash
# Database backups (automatic retention management)
./scripts/backup.sh

# Database restore (interactive)
./scripts/restore.sh

# Data retention cleanup (preview mode by default)
python app/utils/data_retention.py

# Execute cleanup (keeps 3 most recent files per source)
python app/utils/data_retention.py --execute

# Custom retention count
python app/utils/data_retention.py --execute --retention-count 5

# Database optimization
sqlite3 data/jps_aggregate.db "VACUUM; ANALYZE;"

# Database integrity check
sqlite3 data/jps_aggregate.db "PRAGMA integrity_check;"

# Export data to CSV
python -m scripts.export_csv

# Data validation
python scripts/validate_file_naming.py
```

## Prerequisites

**LLM Requirements:**
- Install Ollama from https://ollama.ai/
- Required model: `ollama pull qwen3:latest`

**Python Requirements:**
- Python 3.11+ recommended
- Conda or venv for environment management

**SQLite Configuration:**
- No installation needed (comes with Python)
- Databases stored in `data/` directory
- Automatic backups with retention policy

## Code Quality & CI/CD

### Static Analysis and Linting

**Python Code Quality (configured in `pyproject.toml`):**
- **Ruff**: Fast Python linter with 40+ rule categories (pycodestyle, Pyflakes, isort, pydocstyle, etc.)
- **MyPy**: Static type checking with strict configuration
- **Bandit**: Security vulnerability scanning for Python code
- **Coverage**: Code coverage analysis with HTML and XML reporting

**Frontend Code Quality:**
- **ESLint**: TypeScript/JavaScript linting with React-specific rules
- **TypeScript Compiler**: Strict type checking with `noEmit` flag
- **Prettier**: Code formatting (integrated with ESLint)

**Configuration Files:**
- `pyproject.toml`: Python tools configuration (ruff, mypy, coverage, bandit)
- `frontend-react/eslint.config.js`: ESLint configuration
- `frontend-react/tsconfig.json`: TypeScript configuration
- `.pre-commit-config.yaml`: Pre-commit hooks configuration

### Pre-commit Hooks

Automated quality gates that run before each commit:

```bash
# Install pre-commit hooks (first time setup)
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Update hook versions
pre-commit autoupdate
```

**Hook Categories:**
- **General**: Trailing whitespace, file formatting, large file detection
- **Python**: Ruff linting/formatting, MyPy type checking, Bandit security scan
- **Frontend**: ESLint, TypeScript checking
- **Testing**: pytest (Python changes), Vitest (frontend changes)
- **Security**: NPM audit for frontend dependencies
- **Documentation**: Spell checking, commit message formatting

### CI/CD Pipeline

**GitHub Actions Workflow (`.github/workflows/ci.yml`):**

**Stage 1: Parallel Testing**
- **Python Tests**: Run pytest with coverage, linting, and type checking
- **Frontend Tests**: Run Vitest with coverage, ESLint, and TypeScript compilation

**Stage 2: Integration Testing**
- Cross-system integration tests
- Database integration with SQLite
- API endpoint integration testing

**Stage 3: End-to-End Testing**
- Full application workflow testing with Playwright
- Browser automation testing critical user paths
- Visual regression testing (if configured)

**Stage 4: Security Scanning**
- Python dependency vulnerability scanning with Safety
- Bandit security analysis for Python code
- NPM audit for frontend dependency vulnerabilities

**Coverage Requirements:**
- Backend: 75% minimum coverage (enforced)
- Frontend: 80% minimum coverage (enforced)
- Build fails if coverage drops below thresholds

**Deployment Gates:**
- All tests must pass before deployment
- Security scans must complete without critical issues
- Code coverage thresholds must be met
- No linting errors allowed

### Quality Metrics and Monitoring

**Code Quality Metrics:**
- Test coverage percentage (backend/frontend)
- Cyclomatic complexity (tracked by ruff)
- Type coverage (MyPy strict mode)
- Security vulnerability count (Bandit + Safety + NPM Audit)
- Technical debt indicators (code smells, duplication)

**Performance Monitoring:**
- Test execution time tracking
- Bundle size monitoring (frontend)
- Database query performance (slow query detection)
- Memory usage patterns in tests

**Failure Prevention:**
- Pre-commit hooks catch issues before commits
- CI pipeline prevents broken code from reaching main branch
- Automated dependency updates with testing
- Regular security scanning and vulnerability patching

### Local CI/CD Testing

**Run the full CI/CD pipeline locally before pushing to GitHub:**

The project includes a comprehensive local CI testing infrastructure in the `ci-test/` directory that mirrors the GitHub Actions environment exactly.

**Quick Start:**
```bash
# Run full CI test suite (recommended before pushing)
make test-ci

# Run specific test suites
make test-python      # Python tests only (with linting and type checking)
make test-frontend    # Frontend tests only (with TypeScript and ESLint)
make test-integration # Integration tests only
make test-e2e        # End-to-end tests (requires running services)
make test-all        # All tests including E2E
```

**CI Test Infrastructure:**
- Uses Docker containers with exact versions: Python 3.11, Node 20
- Isolated environment that won't affect your local setup
- Runs tests in the same order as GitHub Actions
- Includes all linting, type checking, and security scans

**Additional CI Commands:**
```bash
# Fix TypeScript type errors automatically
make fix-types

# Clean test artifacts and caches
make clean

# Build CI test containers
make build-ci

# Stop CI test containers
make stop-ci
```

**Test Script Options:**
```bash
# Direct script usage (from project root)
./ci-test/test-ci-local.sh [OPTIONS]

OPTIONS:
    -p, --python-only       Run only Python tests
    -f, --frontend-only     Run only frontend tests
    -i, --integration-only  Run only integration tests
    -e, --e2e              Include E2E tests
    -a, --all              Run all tests including E2E
    -h, --help             Show help message
```

**Using Act for GitHub Actions Testing (Optional):**
```bash
# Install act tool
make install-act

# Run actual GitHub Actions workflow locally
make test-with-act
```

**Troubleshooting Local CI:**
- If tests pass locally but fail in GitHub Actions (or vice versa):
  - Update Docker images: `docker-compose -f ci-test/docker-compose.test.yml pull`
  - Clean and rebuild: `make clean && make build-ci`
  - Check Python version: CI uses 3.11, not 3.12
  - Check for uncommitted files that might affect tests
  - Verify environment variables match between local and CI
  - Check if your local development has different dependencies installed

**CI Test Environment Details:**
- Python: 3.11 (exact match with GitHub Actions)
- Node: 20.x (LTS version used in CI)
- SQLite: Built-in with Python (for all tests)
- Operating System: Ubuntu-based containers
- TypeScript: Uses tsconfig.test.json for relaxed test configuration

**Performance Tips:**
- Use `--python-only` or `--frontend-only` flags for faster feedback
- Run `make test-python` while developing Python code
- Run `make test-frontend` while developing React components
- Use `make test-ci` only before pushing for full validation

## Debugging

### Application Error Handling
- Screenshots saved to: `logs/error_screenshots/`
- HTML dumps saved to: `logs/error_html/`
- Logs: `logs/app.log`, `logs/scrapers.log`, `logs/errors.log`

### Test Debugging and Troubleshooting

**Common Test Issues and Solutions:**

**Python/Pytest Issues:**
```bash
# Database connection issues
export DATABASE_URL="sqlite:///test.db"  # Use SQLite for local testing
python -c "from app import create_app; from app.database import db; app = create_app(); app.app_context().push(); db.create_all()"

# Import errors or missing dependencies
pip install -r requirements.txt
pip install pytest-cov pytest-mock pytest-asyncio

# Fixture or mock issues
python -m pytest tests/ -v --setup-show    # Show fixture setup/teardown
python -m pytest tests/ -s                 # Don't capture stdout (show prints)

# Slow tests
python -m pytest tests/ --durations=0      # Show all test durations
python -m pytest tests/ -m "not slow"      # Skip slow tests

# Failed assertions
python -m pytest tests/ -vv --tb=long      # Detailed traceback
python -m pytest tests/ --pdb              # Drop into debugger on failure
```

**Frontend/Vitest Issues:**
```bash
cd frontend-react

# Component rendering issues
npm test -- --no-coverage SomeComponent.test.tsx  # Run without coverage

# Mock issues
npm test -- --reporter=verbose             # Detailed test output
npm test -- --run --reporter=verbose       # Non-interactive verbose mode

# TypeScript errors in tests
npx tsc --noEmit                           # Check TypeScript compilation
npm test -- --typecheck                    # Enable type checking in tests

# Test environment issues
npm test -- --environment=jsdom            # Ensure correct test environment
npm test -- --globals                      # Enable global test APIs
```

**Integration Test Issues:**
```bash
# Database not available
# SQLite requires no setup - just ensure data directory exists
mkdir -p data                             # Create data directory if needed

# LLM service not available  
ollama serve                               # Start Ollama service
ollama pull qwen3:latest                   # Ensure model is available
curl http://localhost:11434/api/tags       # Check Ollama API

# Port conflicts
lsof -i :5001                             # Check what's using Flask port
lsof -i :11434                            # Check what's using Ollama port
```

**E2E Test Issues:**
```bash
cd frontend-react

# Browser installation issues
npx playwright install --with-deps        # Install browsers and dependencies
npx playwright install-deps               # Install system dependencies only

# Test timeout issues
npx playwright test --timeout=60000       # Increase timeout to 60 seconds
npx playwright test --workers=1           # Run tests sequentially

# Visual debugging
npx playwright test --headed              # Run with visible browser
npx playwright test --debug               # Step through tests interactively
npx playwright test --trace on            # Generate detailed traces

# Test artifacts
npx playwright show-report                # View test results
ls test-results/                          # Check test artifacts directory
```

**Performance and Memory Issues:**
```bash
# Memory usage monitoring
python -m pytest tests/ --memray          # Memory profiling (if memray installed)
python -m pytest tests/ -v --tb=no        # Minimal output to reduce memory

# Test parallelization issues
python -m pytest tests/ -n 1              # Run tests sequentially
python -m pytest tests/ --dist=loadfile   # Distribute by file instead of function

# Coverage performance
python -m pytest tests/ --no-cov          # Skip coverage collection
python -m pytest tests/ --cov-config=.coveragerc  # Use custom coverage config
```

**CI/CD Debugging:**
```bash
# Reproduce CI environment locally
act                                        # Run GitHub Actions locally (if act installed)
docker run --rm -it python:3.11 bash     # Test in CI Python environment

# Pre-commit debugging
pre-commit run --all-files --verbose      # Run with detailed output
pre-commit clean                          # Clean pre-commit cache
pre-commit install --install-hooks        # Reinstall hooks

# Security scan false positives
bandit -r app/ --skip B101,B601           # Skip specific security checks
safety check --ignore 12345               # Ignore specific vulnerabilities
```

**Test Data and Fixtures:**
```bash
# Reset test database
python -c "from app import create_app; from app.database import db; app = create_app(); app.app_context().push(); db.drop_all(); db.create_all()"

# Generate test data
python scripts/create_test_data.py         # Create sample data for manual testing
python -m pytest tests/ --fixtures        # Show available fixtures

# Mock data debugging
python -c "from tests.conftest import *; print(sample_prospects())"  # Test fixture generation
```

**Log Analysis:**
```bash
# Test logs
tail -f logs/app.log                       # Follow application logs during tests
grep ERROR logs/app.log                    # Find error messages
grep -A 5 -B 5 "test_function_name" logs/app.log  # Context around specific test

# Frontend test logs
cd frontend-react
npm test -- --reporter=verbose 2>&1 | tee test.log  # Save test output to file
```

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

The project implements a comprehensive testing strategy designed to prevent breaking changes during refactoring and ensure system reliability:

**Multi-Layer Testing Architecture:**
- **Unit Tests**: Individual component and function testing with 75%+ backend coverage requirement
- **Integration Tests**: Database operations, API endpoint testing, and service layer integration
- **Component Tests**: Frontend React component testing with user interaction simulation
- **End-to-End Tests**: Full application workflow testing with Playwright
- **Security Tests**: Vulnerability scanning for dependencies and code security analysis
- **Performance Tests**: Load testing for large datasets and virtual scrolling validation

**Testing Frameworks:**
- **Backend**: pytest with coverage reporting, mocking with pytest-mock
- **Frontend**: Vitest with @testing-library for React component testing
- **E2E**: Playwright for browser automation and user workflow testing
- **Security**: Bandit for Python security scanning, npm audit for frontend dependencies

**Coverage Requirements:**
- Backend: Minimum 75% test coverage (enforced in CI)
- Frontend Components: Minimum 80% test coverage (enforced in CI)
- Critical paths: 90%+ coverage for core business logic

**Test Organization:**
```
tests/
├── database/           # Database model and operation tests
├── api/               # API endpoint and route tests  
├── core/              # Scraper framework and core logic tests
├── services/          # Service layer integration tests
├── utils/             # Utility function tests
└── integration/       # Cross-system integration tests

frontend-react/src/
├── components/        # Component test files (*.test.tsx)
├── hooks/            # Custom hooks tests
├── contexts/         # Context and state management tests
└── test/             # Test utilities and setup
```

**Automated Testing Pipeline:**
- **Pre-commit Hooks**: Run tests, linting, and security scans before commits
- **CI/CD Pipeline**: Multi-stage testing with GitHub Actions
- **Parallel Testing**: Backend and frontend tests run concurrently for speed
- **Test Isolation**: Each test suite runs in isolated environments
- **Failure Fast**: Pipeline stops on first critical failure to save resources

**Comprehensive Test Coverage:**

**Backend Tests (`tests/` directory):**
- `database/test_models.py`: Database model relationships, validations, cascade deletes
- `api/test_prospects_api.py`: Prospects API endpoints with pagination, filtering, security
- `api/test_decisions_api.py`: Decision CRUD operations, validation, bulk operations
- `core/test_consolidated_scraper_base.py`: Scraper framework, browser automation, data processing
- `services/test_llm_service.py`: LLM integration, error handling, response parsing
- `services/test_enhancement_queue.py`: Queue management, progress tracking, status monitoring
- `utils/test_value_and_date_parsing.py`: Contract value parsing, date formatting, edge cases
- `utils/test_naics_lookup.py`: NAICS code validation, search, hierarchy traversal
- `integration/test_llm_api_integration.py`: End-to-end LLM workflow testing

**Frontend Tests (`frontend-react/src/components/` directory):**
- `ProspectTable.test.tsx`: Data table virtualization, sorting, enhancement buttons, accessibility
- `ProspectFilters.test.tsx`: Filter interactions, data source selection, AI enhancement toggles
- `AIEnrichment.test.tsx`: Status dashboard, progress tracking, LLM output display, controls
- `GoNoGoDecision.test.tsx`: Decision workflows, compact/full modes, reason validation
- `Navigation.test.tsx`: User authentication states, admin navigation, responsive design
- `EnhancementButton.test.tsx`: Button states, loading indicators, error handling
- `ProspectDetailsModal.test.tsx`: Modal interactions, data display, form validation

**Test Coverage Areas:**
- **User Interactions**: Click events, form submissions, keyboard navigation
- **Error States**: Network failures, validation errors, loading states
- **Edge Cases**: Null data, empty states, boundary conditions, malformed inputs
- **Accessibility**: ARIA attributes, keyboard navigation, screen reader compatibility
- **Performance**: Large datasets, virtual scrolling, memory usage patterns
- **Security**: SQL injection prevention, XSS protection, input sanitization
- **Integration**: Database operations, API communication, external service integration

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

## Project Structure

The project has been organized for clarity and maintainability:

```
/
├── README.md              # Main project documentation
├── CLAUDE.md             # This file - Claude-specific instructions
├── Dockerfile            # Main Docker image definition
├── docker-compose.yml    # Main compose configuration
├── Makefile             # Includes CI test commands
├── requirements.txt      # Python dependencies
├── pyproject.toml       # Python project configuration
├── pytest.ini           # Pytest configuration
├── run.py               # Main application entry point
├── app/                 # Application source code
│   ├── api/            # API endpoints
│   ├── core/           # Core scraper framework
│   ├── database/       # Database models and operations
│   ├── services/       # Business logic services
│   └── utils/          # Utility functions
├── frontend-react/      # React TypeScript frontend
├── tests/              # Backend test files
├── scripts/            # Utility and maintenance scripts
├── migrations/         # Database migrations (Alembic)
├── ci-test/           # Local CI/CD testing infrastructure
│   ├── test-ci-local.sh        # Main test runner script
│   ├── docker-compose.test.yml # Test environment config
│   ├── Dockerfile.*-test       # Test container definitions
│   ├── Makefile               # CI test commands
│   ├── README.md              # CI testing documentation
│   └── .actrc                 # Act configuration (for GitHub Actions local testing)
├── docker/            # Docker-related files
│   ├── entrypoint.sh          # Container entrypoint
│   ├── docker-build.sh        # Build and deploy script
│   ├── docker-start.*         # Start scripts (sh/ps1)
│   ├── docker-compose-minimal.yml # Minimal setup option
│   └── *.md                   # Docker documentation
├── docs/              # Project documentation
│   ├── ARCHITECTURE.md        # System architecture
│   ├── TESTING.md            # Testing guide
│   ├── REFACTORING_SUMMARY.md # Refactoring history
│   └── *.md                  # Other documentation
├── data/              # Data storage
│   ├── raw/           # Raw scraped files
│   └── processed/     # Processed exports
├── logs/              # Application logs
├── sql/               # SQL scripts
└── backups/           # Database backups
```

**Key Directories:**
- `ci-test/`: Everything needed for local CI/CD testing
- `docker/`: All Docker-related scripts and configurations
- `docs/`: All project documentation (except README.md and CLAUDE.md)
- `app/`: Python application code
- `frontend-react/`: React frontend application
- `scripts/`: Utility scripts for maintenance and operations