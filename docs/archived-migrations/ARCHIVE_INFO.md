# Archived Migrations

This directory contains historical migrations that are no longer part of the active migration chain but are preserved for reference.

## Why Archive Migrations?

1. **Historical Reference**: Understanding past schema evolution
2. **Rollback Safety**: In case we need to understand old data structures
3. **Documentation**: These migrations document features that were added/removed
4. **Clean Active Migrations**: Keeps the main migrations folder focused on current schema

## Archived Files

- **add_role_column_to_users.py** - User role management addition
- **backfill_file_logs.py** - Historical data population for file processing
- **backfill_naics_descriptions.py** - NAICS code description updates
- **create_llm_output_table.py** - LLM enhancement tracking table
- **fix_prospect_titles.py** - Data quality improvements for titles
- **infer_missing_data.py** - Smart data inference for incomplete records
- **migrate_contract_fields.py** - Contract-related field migrations
- **normalize_naics_codes.py** - NAICS code standardization
- **standardize_naics_formatting.py** - NAICS format consistency

## Note

These migrations have already been applied to production databases and their changes are incorporated in the current schema defined in `000_create_base_tables.py`.