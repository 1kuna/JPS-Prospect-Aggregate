# Migration Checklist

## Pre-Migration Checklist

### 1. Environment Preparation
- [ ] Verify Docker and Docker Compose are installed
- [ ] Ensure Python 3.11 environment is active
- [ ] Install psycopg2-binary: `pip install psycopg2-binary`
- [ ] Create `.env` file with PostgreSQL credentials
- [ ] Verify disk space (need 3x current database size)

### 2. Backup Current System
- [ ] Full backup of SQLite databases
  ```bash
  cp data/jps_aggregate.db backups/migration/jps_aggregate_$(date +%Y%m%d_%H%M%S).db
  cp data/jps_users.db backups/migration/jps_users_$(date +%Y%m%d_%H%M%S).db
  ```
- [ ] Export current data to CSV for verification
  ```bash
  python -m scripts.export_csv
  ```
- [ ] Document current database sizes
- [ ] Save current application configuration

### 3. Test Migration (Staging)
- [ ] Set up test PostgreSQL containers
- [ ] Run migration script in test mode
- [ ] Verify data integrity
- [ ] Test application functionality
- [ ] Run all unit tests
- [ ] Performance benchmarking

### 4. Communication
- [ ] Schedule maintenance window
- [ ] Notify all users of planned downtime
- [ ] Prepare rollback communication plan
- [ ] Document support contact information

## Migration Steps

### 1. Stop Application Services
- [ ] Stop web server: `systemctl stop jps-aggregate`
- [ ] Stop any scheduled jobs/cron tasks
- [ ] Verify no active database connections
- [ ] Create final pre-migration backup

### 2. Deploy PostgreSQL Infrastructure
- [ ] Start PostgreSQL containers
  ```bash
  docker-compose up -d
  ```
- [ ] Verify containers are healthy
  ```bash
  docker-compose ps
  docker-compose logs postgres-business
  docker-compose logs postgres-users
  ```
- [ ] Test database connections
  ```bash
  docker exec -it jps_postgres_business psql -U ${POSTGRES_BUSINESS_USER} -d jps_aggregate -c "SELECT 1;"
  docker exec -it jps_postgres_users psql -U ${POSTGRES_USERS_USER} -d jps_users -c "SELECT 1;"
  ```

### 3. Run Database Migration
- [ ] Execute migration script
  ```bash
  cd /opt/jps
  python scripts/migration/sqlite_to_postgres.py
  ```
- [ ] Monitor migration progress
- [ ] Check migration.log for errors
- [ ] Verify row counts match

### 4. Update Application Configuration
- [ ] Update database URLs in `.env`
  ```bash
  cp .env .env
  ```
- [ ] Update Alembic configuration
  ```bash
  python scripts/migration/update_alembic.py
  ```
- [ ] Run Alembic migrations
  ```bash
  alembic upgrade head
  ```

### 5. Verify Application
- [ ] Start application with PostgreSQL
  ```bash
  systemctl start jps-aggregate
  ```
- [ ] Check application logs for errors
- [ ] Test core functionality:
  - [ ] User authentication
  - [ ] Prospect listing and search
  - [ ] Scraper execution
  - [ ] Decision tracking
  - [ ] File downloads
- [ ] Verify performance metrics

### 6. Enable Automated Processes
- [ ] Enable backup cron job
  ```bash
  crontab -e
  # Add: 0 2 * * * /opt/jps/scripts/backup/backup.sh
  ```
- [ ] Re-enable scraper schedules
- [ ] Start monitoring scripts
- [ ] Verify health checks

## Post-Migration Checklist

### 1. Monitoring (First 24 Hours)
- [ ] Monitor application logs continuously
- [ ] Check database performance metrics
- [ ] Monitor connection pool usage
- [ ] Track query performance
- [ ] Check backup completion

### 2. Performance Optimization
- [ ] Run ANALYZE on all tables
  ```bash
  docker exec -it jps_postgres_business psql -U ${POSTGRES_BUSINESS_USER} -d jps_aggregate -c "ANALYZE;"
  ```
- [ ] Review slow query log
- [ ] Optimize indexes if needed
- [ ] Adjust PostgreSQL configuration

### 3. Documentation Updates
- [ ] Update README with PostgreSQL information
- [ ] Document new backup/restore procedures
- [ ] Update deployment documentation
- [ ] Create troubleshooting guide

### 4. Cleanup (After 30 Days)
- [ ] Remove SQLite database files
- [ ] Archive migration logs
- [ ] Remove migration scripts from production
- [ ] Update CI/CD pipelines

## Rollback Procedures

If issues are encountered, follow these steps:

### 1. Immediate Rollback (< 1 hour)
- [ ] Stop application
- [ ] Restore SQLite databases from backup
- [ ] Update configuration to use SQLite
- [ ] Restart application
- [ ] Notify users of rollback

### 2. Rollback After Extended Use
- [ ] Export any new data from PostgreSQL
- [ ] Merge new data into SQLite backup
- [ ] Follow immediate rollback steps
- [ ] Document issues for retry

### Emergency Contacts
- Database Admin: [Contact Info]
- Application Owner: [Contact Info]
- DevOps Team: [Contact Info]

## Sign-off

- [ ] Migration completed successfully
- [ ] All tests passed
- [ ] Performance acceptable
- [ ] Backups verified
- [ ] Documentation updated

Migrated by: _________________________ Date: _____________

Verified by: _________________________ Date: _____________