# Docker Migration Fix Instructions

## Summary of Changes

I've fixed the Docker migration issues by:

1. **Updated TWO problematic migrations** to safely handle existing columns:
   - `fbc0e1fbf50d` - for estimated_value_text and related columns
   - `5fb5cc7eff5b` - for ai_enhanced_title column
2. **Fixed docker-compose.yml** database creation syntax error
3. **Enhanced the Docker entrypoint** to handle multiple duplicate column scenarios
4. **Created repair scripts** for fixing migration state issues

## How to Deploy the Fix

### Option 1: Clean Deployment (Recommended)

1. **On your Mac, commit and push the changes:**
   ```bash
   git add -A
   git commit -m "Fix Docker migration issues with safe column handling"
   git push origin main
   ```

2. **On the Windows machine, pull and rebuild:**
   ```powershell
   # Stop existing containers
   docker-compose down
   
   # Pull latest changes
   git pull origin main
   
   # Rebuild with new fixes
   docker-compose build --no-cache
   
   # Start fresh
   docker-compose up -d
   ```

### Option 2: Fix Existing Installation (Windows PowerShell)

If you want to fix the existing installation:

1. **Push the changes from your Mac** (same as Option 1, step 1)

2. **On Windows, pull changes and run the health check:**
   ```powershell
   # Pull latest changes
   git pull origin main
   
   # Check current status
   .\scripts\health_check.ps1
   ```

3. **Choose your fix strategy:**
   ```powershell
   # Run the reset script (gives you options)
   .\scripts\windows_docker_reset.ps1
   ```
   
   This script offers:
   - **Soft reset**: Preserve data, fix migrations
   - **Nuclear reset**: Delete everything and start fresh

### Option 2b: Nuclear Reset (If Everything Else Fails)

If migrations are completely broken:

```powershell
# This DESTROYS ALL DATA but guarantees a fresh start
.\scripts\nuclear_reset.ps1
```

### Option 3: Manual Fix (if scripts don't work)

1. **Connect to the database:**
   ```powershell
   docker-compose exec db psql -U jps_user -d jps_prospects
   ```

2. **Check if alembic_version table exists:**
   ```sql
   SELECT * FROM alembic_version;
   ```

3. **If it doesn't exist, create it:**
   ```sql
   CREATE TABLE alembic_version (
       version_num VARCHAR(32) NOT NULL,
       CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
   );
   ```

4. **Mark the problematic migration as complete:**
   ```sql
   INSERT INTO alembic_version (version_num) VALUES ('fbc0e1fbf50d');
   ```

5. **Exit psql and run remaining migrations:**
   ```powershell
   docker-compose exec web flask db upgrade
   ```

## What Was Fixed

### The Problem
- The migration `fbc0e1fbf50d` was trying to add columns that already existed
- This happened because `000_create_base_tables` already created these columns
- PostgreSQL throws an error when trying to add duplicate columns

### The Solution
1. **Safe Column Addition**: Modified the migration to check if columns exist before adding them
2. **Graceful Error Handling**: Updated Docker entrypoint to continue even if some migrations fail
3. **Repair Tools**: Created scripts to fix migration state when needed

## Verification

After applying the fix, verify everything is working:

```powershell
# Check container status
docker-compose ps

# Check migration status
docker-compose exec web flask db current

# Check application logs
docker-compose logs -f web

# Test the application
curl http://localhost:5001/health
```

## Troubleshooting

If you still see errors:

1. **Check the logs carefully:**
   ```powershell
   docker-compose logs db | grep ERROR
   docker-compose logs web | grep ERROR
   ```

2. **Try a complete reset** (WARNING: This will delete all data):
   ```powershell
   docker-compose down -v
   docker-compose up --build -d
   ```

3. **Use the repair script:**
   ```powershell
   docker-compose exec web python scripts/repair_migrations.py --fix
   ```

## Prevention

To prevent this in the future:
- Always use safe column operations in migrations
- Test migrations on both fresh and existing databases
- Use the helper functions in `migrations/alembic_helpers.py`

## Files Changed

### Migration Fixes
- `/migrations/versions/fbc0e1fbf50d_add_contract_mapping_fields_and_llm_.py` - Made column additions safe
- `/migrations/versions/5fb5cc7eff5b_add_ai_enhanced_title_field_to_.py` - Made ai_enhanced_title addition safe
- `/migrations/versions/d1def2efebc3_revert_proposal_to_prospect_model_and_.py` - Fixed inferred_office column drop error
- `/migrations/alembic_helpers.py` - Created helper functions for safe migrations

### Docker Configuration
- `/docker-compose.yml` - Fixed PostgreSQL database creation syntax
- `/Dockerfile` - Enhanced entrypoint script with robust error handling and fallback logic

### Management Scripts
- `/scripts/repair_migrations.py` - Python script to repair migration issues
- `/scripts/docker_migration_fix.sh` - Bash script for Docker environments
- `/scripts/windows_docker_reset.ps1` - PowerShell script with soft/nuclear reset options
- `/scripts/nuclear_reset.ps1` - Complete system reset script (destroys all data)
- `/scripts/health_check.ps1` - Quick system health diagnostic script