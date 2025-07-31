# Testing & CI/CD Setup

This document describes the comprehensive testing and CI/CD infrastructure implemented to prevent breaking changes during refactoring.

## Overview

The testing strategy includes:
- **Unit Tests**: Individual component and service testing
- **Integration Tests**: API and database interaction testing  
- **End-to-End Tests**: Full user workflow testing
- **Static Analysis**: Code quality and security scanning
- **Continuous Integration**: Automated testing on every commit/PR

## Quick Start

### 1. Install Dependencies

```bash
# Backend dependencies including test tools
pip install -r requirements.txt

# Frontend dependencies
cd frontend-react && npm install

# Install Playwright for E2E tests
cd frontend-react && npx playwright install --with-deps
```

### 2. Set up Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install the git hook scripts
pre-commit install

# Optional: run against all files
pre-commit run --all-files
```

### 3. Run Tests

```bash
# Backend unit tests
python -m pytest tests/ -v

# Backend unit tests with coverage
python -m pytest tests/ -v --cov=app --cov-report=html

# Frontend unit tests
cd frontend-react && npm run test

# Frontend tests with coverage
cd frontend-react && npm run test:coverage

# E2E tests (requires both servers running)
cd frontend-react && npx playwright test

# Integration tests
python -m pytest tests/integration/ -v -m integration
```

## Test Structure

### Backend Tests (`tests/`)

```
tests/
├── conftest.py                 # Shared fixtures and setup
├── services/                   # Service unit tests
│   ├── test_llm_service.py    # LLM service tests
│   └── test_enhancement_queue.py # Queue management tests
├── api/                        # API endpoint tests
│   └── test_llm_processing.py # LLM API tests
├── integration/                # Integration tests
│   └── test_llm_api_integration.py # API + DB tests
└── core/                       # Existing scraper tests
    └── scrapers/
```

### Frontend Tests (`frontend-react/`)

```
frontend-react/
├── src/
│   ├── components/
│   │   ├── ProspectDetailsModal.test.tsx
│   │   └── EnhancementButton.test.tsx
│   └── test/
│       ├── setup.ts           # Test configuration
│       └── example.test.tsx   # Example test
└── tests/
    └── e2e/                   # Playwright E2E tests
        ├── global-setup.ts
        ├── global-teardown.ts
        └── prospect-enhancement.spec.ts
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) includes:

### 1. Python Tests & Linting
- **Linting**: Ruff for fast Python linting
- **Type Checking**: MyPy for static type analysis
- **Unit Tests**: Pytest with 75% coverage requirement
- **Security**: Bandit security scanning

### 2. Frontend Tests & Linting
- **Type Checking**: TypeScript compiler
- **Linting**: ESLint with zero warnings policy
- **Unit Tests**: Vitest with coverage reporting
- **Build Verification**: Production build test

### 3. Integration Tests
- **Database Tests**: Real PostgreSQL integration
- **API Tests**: Full request/response cycle testing
- **Service Integration**: Cross-service communication tests

### 4. End-to-End Tests
- **User Workflows**: Complete feature testing
- **Browser Testing**: Chrome, Firefox, Safari, Mobile
- **Visual Testing**: Screenshot comparison on failures

### 5. Security Scanning
- **Python Dependencies**: Safety vulnerability scanning
- **Frontend Dependencies**: NPM audit
- **Code Security**: Bandit static analysis

## Pre-commit Hooks

The pre-commit configuration includes:

### Code Quality
- **Trailing whitespace removal**
- **End-of-file fixing** 
- **YAML/JSON validation**
- **Large file detection**
- **Merge conflict detection**

### Python Checks
- **Ruff linting and formatting**
- **MyPy type checking**
- **Bandit security scanning**
- **Pytest execution** (on Python changes)

### Frontend Checks
- **ESLint validation**
- **TypeScript type checking**
- **Vitest execution** (on frontend changes)
- **NPM audit** (on dependency changes)

### Documentation
- **Spell checking**
- **Commit message formatting**

## Coverage Requirements

### Backend Coverage
- **Minimum**: 75% overall coverage
- **Critical Services**: 90%+ coverage for LLM and queue services
- **API Endpoints**: 85%+ coverage for all endpoints

### Frontend Coverage
- **Components**: 80%+ coverage for UI components
- **Hooks**: 90%+ coverage for custom hooks
- **Utilities**: 95%+ coverage for utility functions

## Running Specific Test Categories

### Unit Tests Only

```bash
# Backend unit tests (excluding integration)
python -m pytest tests/ -v -m "not integration"

# Frontend unit tests
cd frontend-react && npm run test
```

### Integration Tests Only

```bash
# Backend integration tests
python -m pytest tests/integration/ -v -m integration

# API integration tests specifically
python -m pytest tests/integration/test_llm_api_integration.py -v
```

### End-to-End Tests

```bash
# Run all E2E tests
cd frontend-react && npx playwright test

# Run specific E2E test
cd frontend-react && npx playwright test prospect-enhancement.spec.ts

# Run E2E tests in headed mode (see browser)
cd frontend-react && npx playwright test --headed

# Debug E2E tests
cd frontend-react && npx playwright test --debug
```

## Test Data Management

### Backend Test Data
- **Fixtures**: Defined in `tests/conftest.py`
- **Database**: Automatic SQLite/PostgreSQL test database
- **Isolation**: Each test gets fresh database state
- **Mocking**: External services mocked (Ollama, etc.)

### Frontend Test Data
- **Mock Data**: Defined in test setup files
- **API Mocking**: MSW (Mock Service Worker) for API calls
- **Component Props**: Factory functions for test props

## Debugging Failed Tests

### Backend Test Failures

```bash
# Run with verbose output and stop on first failure
python -m pytest tests/ -v -x

# Run specific test with debug output
python -m pytest tests/services/test_llm_service.py::TestLLMService::test_enhance_prospect_individual -v -s

# Run with coverage and HTML report
python -m pytest tests/ --cov=app --cov-report=html
# Open htmlcov/index.html to see coverage
```

### Frontend Test Failures

```bash
# Run tests in watch mode
cd frontend-react && npm run test

# Run with UI (browser-based test runner)
cd frontend-react && npm run test:ui

# Run with coverage
cd frontend-react && npm run test:coverage
```

### E2E Test Failures

```bash
# Run with trace on failure
cd frontend-react && npx playwright test --trace on

# Show test report (after test run)
cd frontend-react && npx playwright show-report

# Run in debug mode with browser
cd frontend-react && npx playwright test --debug --headed
```

## CI/CD Troubleshooting

### Common CI Failures

1. **Coverage Drop**: Check coverage report, add missing tests
2. **Linting Errors**: Run `ruff check app/ --fix` locally
3. **Type Errors**: Run `mypy app/` locally to see issues
4. **Frontend Build**: Check TypeScript errors with `npx tsc --noEmit`
5. **E2E Timeouts**: Increase timeouts or fix race conditions

### Local CI Simulation

```bash
# Run the same checks as CI locally
ruff check app/ --output-format=github
ruff format app/ --check
mypy app/ --ignore-missing-imports
python -m pytest tests/ -v --cov=app --cov-fail-under=75

cd frontend-react
npx tsc --noEmit
npm run lint -- --max-warnings 0
npm run test:coverage -- --run
npm run build
```

## Performance Testing

### Load Testing
- Use `locust` or similar tools for API load testing
- Monitor database performance under load
- Test queue processing with high volumes

### Frontend Performance
- Lighthouse CI integration for performance regression detection
- Bundle size monitoring
- Core Web Vitals tracking

## Security Testing

### Backend Security
- **Bandit**: Static security analysis
- **Safety**: Dependency vulnerability scanning
- **OWASP**: Security header validation

### Frontend Security
- **NPM Audit**: Dependency vulnerability scanning
- **CSP**: Content Security Policy validation
- **XSS**: Cross-site scripting protection testing

## Monitoring and Alerting

### Test Results
- GitHub PR status checks prevent merging on test failures
- Coverage reports uploaded to Codecov
- Test trends tracked over time

### Performance Monitoring
- Build time tracking
- Test execution time monitoring
- Coverage trend analysis

This comprehensive testing infrastructure ensures that refactoring changes are caught before they reach production, preventing the kind of breakage experienced with the recent LLM service refactor.