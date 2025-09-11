# Testing Guide

## Overview
This project follows Test-Driven Development (TDD) principles with comprehensive test coverage across backend, frontend, and integration layers.

## Quick Start

### Run All Tests
```bash
# Backend tests
pytest

# Frontend tests
cd frontend-react && npm test

# Full CI suite locally
make test-ci
```

### Run Specific Test Types
```bash
# Fast unit tests only
pytest -m unit

# Integration tests (slower, may use database)
pytest -m integration

# Scraper tests
pytest -m scraper

# Security tests
pytest -m security

# Performance benchmarks
pytest -m performance

# Exclude slow tests
pytest -m "not slow"

# Combine markers
pytest -m "unit and not slow"
```

## Test Organization

### Backend Tests (`/tests/`)
```
tests/
├── api/                    # API endpoint tests
│   ├── test_decisions_api.py
│   ├── test_prospects_api.py
│   └── test_llm_*.py
├── core/                   # Core functionality
│   ├── scrapers/          # Scraper tests
│   └── test_*.py
├── database/              # Database tests
│   └── test_migrations.py
├── services/              # Service layer tests
├── security/              # Security tests
├── performance/           # Performance tests
├── utils/                 # Utility tests
├── fixtures/              # Test data files
│   ├── *.csv
│   ├── *.json
│   └── *.xlsx
├── conftest.py            # Shared fixtures
└── factories.py           # Test data factories
```

### Frontend Tests (`/frontend-react/tests/`)
```
frontend-react/tests/
├── integration/           # Integration tests
│   ├── ProspectWorkflow.test.tsx
│   └── DecisionWorkflow.test.tsx
└── unit/                  # Component unit tests
```

## Test Markers

Tests are categorized with markers for selective execution:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Tests requiring database/external services
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.scraper` - Scraper-specific tests
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.security` - Security tests
- `@pytest.mark.performance` - Performance benchmarks

## Key Test Fixtures

### Authentication
```python
def test_user_access(auth_client):
    """Test with default user role."""
    response = auth_client.get('/api/protected')
    
def test_admin_access(admin_client):
    """Test with admin role."""
    response = admin_client.get('/api/admin')
```

### Database
```python
def test_with_database(db_session):
    """Test with transactional database session."""
    # Changes are rolled back after test
```

### Test Data Factories
```python
from tests.factories import ProspectFactory, UserFactory

def test_prospect_creation():
    prospect = ProspectFactory.create(
        title="Custom Title",
        agency="NASA"
    )
```

## Coverage Requirements

- Backend: 80% minimum (enforced in CI)
- Frontend: 80% minimum
- Critical paths: 95%+ recommended

### View Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open report
open htmlcov/index.html

# Terminal report with missing lines
pytest --cov=app --cov-report=term-missing
```

## CI/CD Pipeline

The CI pipeline runs tests in parallel for faster feedback:

1. **Python Unit Tests** (fast)
   - Linting (ruff)
   - Type checking (mypy)
   - Unit tests only

2. **Python Integration Tests** (slower)
   - Integration tests
   - Scraper tests
   - Performance tests

3. **Frontend Tests**
   - TypeScript checking
   - ESLint
   - Unit & integration tests

4. **E2E Tests**
   - Full stack testing
   - Browser automation

## Writing Tests

### Test Principles
1. **Deterministic**: No random data in tests
2. **Isolated**: Tests don't depend on each other
3. **Fast**: Use mocks for external services
4. **Clear**: Descriptive names and assertions
5. **Complete**: Test happy path and edge cases

### Example Test Structure
```python
import pytest
from tests.factories import ProspectFactory

@pytest.mark.unit
class TestProspectService:
    """Test prospect service functionality."""
    
    def test_create_prospect_success(self, db_session):
        """Test successful prospect creation."""
        # Arrange
        data = ProspectFactory.build()
        
        # Act
        result = create_prospect(data)
        
        # Assert
        assert result.id is not None
        assert result.title == data['title']
    
    def test_create_prospect_validation_error(self):
        """Test prospect creation with invalid data."""
        # Arrange
        invalid_data = {'title': ''}  # Missing required fields
        
        # Act & Assert
        with pytest.raises(ValidationError):
            create_prospect(invalid_data)
```

## Debugging Tests

### Run specific test
```bash
pytest tests/api/test_prospects_api.py::TestProspectsAPI::test_get_prospects
```

### Verbose output
```bash
pytest -vv tests/
```

### Show print statements
```bash
pytest -s tests/
```

### Stop on first failure
```bash
pytest -x tests/
```

### Drop into debugger on failure
```bash
pytest --pdb tests/
```

## Test Data Management

### Fixtures Directory
Static test data files are stored in `tests/fixtures/`:
- CSV files for scrapers
- JSON for API responses
- Excel files for data imports

### Factories
Dynamic test data generation using factories:
```python
# Deterministic data based on index
prospect1 = ProspectFactory.create()  # First prospect
prospect2 = ProspectFactory.create()  # Second prospect

# Override specific fields
custom = ProspectFactory.create(
    agency="Custom Agency",
    naics="541511"
)
```

## Performance Testing

### Run benchmarks
```bash
pytest tests/performance/ -v
```

### Profile slow tests
```bash
pytest --durations=10  # Show 10 slowest tests
```

## Security Testing

Security tests check for:
- SQL injection prevention
- XSS protection
- Authentication/authorization
- Input validation
- Security headers

```bash
pytest tests/security/ -v
```

## Troubleshooting

### Common Issues

**Import errors**
```bash
# Ensure project root is in PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

**Database locked**
```bash
# Reset test database
rm test_*.db
python -c "from app import create_app; from app.database import db; app = create_app(); app.app_context().push(); db.create_all()"
```

**Flaky tests**
- Check for random data usage
- Ensure proper test isolation
- Use deterministic factories

**Coverage gaps**
```bash
# Find untested code
pytest --cov=app --cov-report=term-missing | grep -E "^\w+\.py"
```

## Best Practices

1. **Use markers consistently** - Help others run relevant tests
2. **Mock external services** - Tests should work offline
3. **Clean up resources** - Use fixtures with proper teardown
4. **Test edge cases** - Empty data, nulls, invalid input
5. **Keep tests fast** - Target < 1 second per unit test
6. **Document complex tests** - Add docstrings for non-obvious logic
7. **Review test failures** - Don't ignore intermittent failures

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Ensure tests pass locally
3. Check coverage hasn't decreased
4. Add appropriate markers
5. Update this documentation if needed

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)
- [TDD Guide](https://www.obeythetestinggoat.com/)