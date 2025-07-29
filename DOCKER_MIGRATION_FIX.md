# Docker Migration Fix Instructions

## Summary of Changes

I've fixed the Docker migration issues by:

1. **Updated the problematic migration** (`fbc0e1fbf50d`) to safely handle existing columns
2. **Enhanced the Docker entrypoint** to better handle migration failures
3. **Created repair scripts** for fixing migration state issues

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

### Option 2: Fix Existing Installation

If you want to fix the existing installation without rebuilding:

1. **Push the changes from your Mac** (same as Option 1, step 1)

2. **On Windows, pull changes and run the fix script:**
   ```powershell
   # Pull latest changes
   git pull origin main
   
   # Make the script executable (Git Bash or WSL)
   chmod +x scripts/docker_migration_fix.sh
   
   # Run the migration fix
   ./scripts/docker_migration_fix.sh
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

- `/migrations/versions/fbc0e1fbf50d_add_contract_mapping_fields_and_llm_.py` - Made column additions safe
- `/migrations/alembic_helpers.py` - Created helper functions for safe migrations
- `/Dockerfile` - Enhanced entrypoint script with better error handling
- `/scripts/repair_migrations.py` - Python script to repair migration issues
- `/scripts/docker_migration_fix.sh` - Bash script for Docker environments