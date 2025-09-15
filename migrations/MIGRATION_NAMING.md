# Migration Naming Convention

This project uses a hybrid migration naming approach:

## Standard Alembic Format
Most migrations follow the standard Alembic naming pattern:
- `{revision_id}_{description}.py`
- Example: `a6bc8592cdf2_merge_heads.py`, `4627cb27031b_add_scraper_key_to_datasource_model.py`

## Special Migrations
Some migrations use special naming for clarity:

### Numbered Migrations
- `000_create_base_tables.py` - Initial schema creation (always runs first)
- `999_final_merge_all_heads.py` - Final merge to resolve any branch conflicts

### Descriptive Names
- `add_file_processing_log_table.py` - Clear feature additions
- `add_settings_table_for_maintenance_mode.py` - Specific feature migrations
- `align_numeric_and_json_types.py` - Data type corrections
- `merge_final_and_align_heads.py` - Merge operations

## Why This Approach?
1. **Readability**: Descriptive names make it easier to understand migration purpose
2. **Ordering**: Numbered migrations ensure critical operations run in correct order
3. **Compatibility**: Alembic still tracks all migrations by revision ID internally
4. **History**: Clear migration history without needing to inspect each file

## Best Practices
- Use standard Alembic format for regular schema changes
- Use descriptive names for complex operations or feature additions
- Use numbered format only for critical ordering requirements
- Always include clear descriptions in migration docstrings