# Scripts Directory

This directory contains utility scripts for managing and operating the JPS Prospect Aggregate system.

## Directory Structure

### setup/
Initial setup and configuration scripts that are typically run once during installation.

- **setup_databases.py** - Initialize both user and business databases, run migrations
- **populate_data_sources.py** - Populate initial data source configurations
- **create_missing_tables.py** - Create any missing database tables

### scrapers/
Scripts for running and testing web scrapers.

- **run_scraper.py** - Run a specific scraper by source name
  ```bash
  python -m scripts.scrapers.run_scraper --source "DHS"
  ```
- **run_all_scrapers.py** - Execute all configured scrapers sequentially
- **test_scraper_individual.py** - Test a specific scraper in isolation
  ```bash
  python scripts/scrapers/test_scraper_individual.py --scraper dhs
  ```
- **monitor_scrapers.py** - Monitor scraper status and health

### database/
Database management and maintenance utilities.

- **backup.sh** - Backup SQLite databases with compression and retention
  ```bash
  ./scripts/database/backup.sh
  ```
- **restore.sh** - Restore databases from backup files
- **check_schema.py** - Verify database schema integrity
- **repair_migrations.py** - Fix migration issues and conflicts
- **update_alembic.py** - Update Alembic migration configurations

### data_processing/
Data export, analysis, and validation tools.

- **export_db_to_csv.py** - Export database tables to CSV format
  ```bash
  python scripts/data_processing/export_db_to_csv.py
  ```
- **export_decisions_for_llm.py** - Export decision data for LLM training
- **validate_data_extraction.py** - Validate data extraction quality
- **validate_raw_data_mapping.py** - Check field mapping accuracy
- **validate_file_naming.py** - Ensure consistent file naming conventions
- **analyze_field_coverage.py** - Analyze field presence across sources
- **analyze_set_asides.py** - Analyze set-aside categorization
- **check_set_aside_results.py** - Verify set-aside processing results
- **restore_prospects_from_files.py** - Restore prospects from raw data files

### enrichment/
LLM-based data enhancement utilities.

- **enhance_prospects_with_llm.py** - Enhance prospect data using LLM
  ```bash
  python scripts/enrichment/enhance_prospects_with_llm.py values --limit 100
  ```

### operations/
System operations and user management.

- **manage_users.py** - User account management utilities
- **health_check.py** - System health verification

### testing/
Testing utilities and helpers.

- **run_scraper_tests.py** - Run comprehensive scraper test suite

### archive/completed-migrations/
Completed one-time migration scripts kept for historical reference. These scripts have already been executed and their functionality is now part of the main application.

See [archive/completed-migrations/README.md](archive/completed-migrations/README.md) for details.

## Common Usage Patterns

### Initial Setup
```bash
# 1. Initialize databases
python scripts/setup/setup_databases.py

# 2. Populate initial data
python scripts/setup/populate_data_sources.py
```

### Daily Operations
```bash
# Run all scrapers
python scripts/scrapers/run_all_scrapers.py

# Run specific scraper
python -m scripts.scrapers.run_scraper --source "DHS"

# Monitor scraper status
python scripts/scrapers/monitor_scrapers.py

# Backup databases
./scripts/database/backup.sh
```

### Data Management
```bash
# Export data to CSV
python scripts/data_processing/export_db_to_csv.py

# Enhance data with LLM
python scripts/enrichment/enhance_prospects_with_llm.py values

# Validate data quality
python scripts/data_processing/validate_data_extraction.py
```

### Troubleshooting
```bash
# Check database schema
python scripts/database/check_schema.py

# Repair migrations
python scripts/database/repair_migrations.py

# System health check
python scripts/operations/health_check.py
```

## Important Notes

1. **Python Path**: Most scripts automatically add the project root to sys.path for imports
2. **Environment**: Ensure your virtual environment is activated before running scripts
3. **Configuration**: Scripts respect .env file settings
4. **Logs**: Script execution logs are typically written to logs/ directory
5. **Archived Scripts**: Don't run scripts in archive/ - they've already been executed

## Development Guidelines

When adding new scripts:
- Place in the appropriate subdirectory based on purpose
- Include clear docstrings with usage examples
- Add error handling and logging
- Update this README with the new script documentation
- Consider if the script is one-time (archive after use) or recurring