# Local CI Testing

This directory contains scripts and configurations for running the CI/CD pipeline locally before pushing to GitHub.

## Quick Start

```bash
# Run the full CI test suite (recommended before pushing)
make test-ci

# Run only specific test suites
make test-python      # Python tests only
make test-frontend    # Frontend tests only
make test-integration # Integration tests only
```

## Files

- `test-ci-local.sh` - Main test runner script that orchestrates all tests
- `docker-compose.test.yml` - Docker Compose configuration for test services
- `Dockerfile.python-test` - Python test environment (Python 3.11)
- `Dockerfile.frontend-test` - Frontend test environment (Node 20)

## How It Works

1. Creates isolated Docker containers matching GitHub Actions environment
2. Sets up PostgreSQL database for testing
3. Runs tests in the same order as CI pipeline:
   - Python linting (ruff)
   - Python type checking (mypy)
   - Python tests with coverage (pytest)
   - Frontend type checking (TypeScript)
   - Frontend linting (ESLint)
   - Frontend tests with coverage (Vitest)
   - Integration tests
   - (Optional) E2E tests

## Benefits

- **Exact CI Environment**: Uses same Python 3.11 and Node 20 versions as GitHub Actions
- **Fast Feedback**: Find issues before pushing to GitHub
- **Isolated Testing**: Doesn't affect your local development environment
- **Database Testing**: Includes PostgreSQL container for integration tests

## Requirements

- Docker
- Docker Compose
- Make (optional, for convenience commands)

## Troubleshooting

If tests fail locally but pass in CI (or vice versa):

1. Ensure Docker images are up to date: `docker-compose -f ci-test/docker-compose.test.yml pull`
2. Clean test artifacts: `make clean`
3. Rebuild test containers: `make build-ci`

## Using Act (Optional)

To run the actual GitHub Actions workflow locally:

```bash
# Install act
make install-act

# Run GitHub Actions locally
make test-with-act
```

Note: Act requires significant disk space for runner images.