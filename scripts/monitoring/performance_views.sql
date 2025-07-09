-- Performance monitoring views for PostgreSQL
-- Run this script after migration to create helpful monitoring views

-- 1. Table sizes and bloat
CREATE OR REPLACE VIEW v_table_stats AS
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    CASE WHEN n_live_tup > 0 
         THEN round(100.0 * n_dead_tup / n_live_tup, 2)
         ELSE 0
    END AS dead_rows_percent
FROM pg_tables
LEFT JOIN pg_stat_user_tables ON pg_tables.tablename = pg_stat_user_tables.relname
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 2. Index usage statistics
CREATE OR REPLACE VIEW v_index_usage AS
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    CASE WHEN idx_scan = 0 THEN 'UNUSED' ELSE 'USED' END as usage_status
FROM pg_stat_user_indexes
ORDER BY idx_scan, pg_relation_size(indexrelid) DESC;

-- 3. Unused indexes (candidates for removal)
CREATE OR REPLACE VIEW v_unused_indexes AS
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan as scans_since_reset
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexname NOT LIKE '%_pkey'  -- Don't suggest removing primary keys
  AND pg_relation_size(indexrelid) > 1024 * 1024  -- Only show indexes > 1MB
ORDER BY pg_relation_size(indexrelid) DESC;

-- 4. Slow query statistics (requires pg_stat_statements extension)
-- Note: This view will only work if pg_stat_statements is enabled
CREATE OR REPLACE VIEW v_slow_queries AS
SELECT
    query,
    calls,
    round(total_exec_time::numeric, 2) AS total_ms,
    round(mean_exec_time::numeric, 2) AS mean_ms,
    round(stddev_exec_time::numeric, 2) AS stddev_ms,
    round(min_exec_time::numeric, 2) AS min_ms,
    round(max_exec_time::numeric, 2) AS max_ms,
    rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_%'
  AND query NOT LIKE '%COMMIT%'
  AND query NOT LIKE '%BEGIN%'
ORDER BY mean_exec_time DESC
LIMIT 20;

-- 5. Connection statistics by database
CREATE OR REPLACE VIEW v_connection_stats AS
SELECT
    datname as database,
    numbackends as active_connections,
    xact_commit as transactions_committed,
    xact_rollback as transactions_rolled_back,
    blks_read as disk_blocks_read,
    blks_hit as buffer_hits,
    CASE WHEN blks_read + blks_hit > 0 
         THEN round(100.0 * blks_hit / (blks_read + blks_hit), 2)
         ELSE 100
    END AS cache_hit_ratio,
    tup_returned as rows_returned,
    tup_fetched as rows_fetched,
    tup_inserted as rows_inserted,
    tup_updated as rows_updated,
    tup_deleted as rows_deleted
FROM pg_stat_database
WHERE datname NOT IN ('template0', 'template1', 'postgres')
ORDER BY active_connections DESC;

-- 6. Table maintenance needs
CREATE OR REPLACE VIEW v_maintenance_needs AS
SELECT
    schemaname,
    tablename,
    n_dead_tup as dead_tuples,
    n_live_tup as live_tuples,
    CASE WHEN n_live_tup > 0 
         THEN round(100.0 * n_dead_tup / n_live_tup, 2)
         ELSE 0
    END AS dead_tuple_percent,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    CASE 
        WHEN last_autovacuum IS NULL AND last_vacuum IS NULL THEN 'NEVER VACUUMED'
        WHEN n_dead_tup > 10000 AND 
             (last_autovacuum IS NULL OR last_autovacuum < CURRENT_TIMESTAMP - INTERVAL '7 days') THEN 'NEEDS VACUUM'
        ELSE 'OK'
    END as vacuum_status
FROM pg_stat_user_tables
WHERE n_live_tup > 1000
ORDER BY dead_tuple_percent DESC, n_dead_tup DESC;

-- 7. Lock monitoring
CREATE OR REPLACE VIEW v_locks AS
SELECT
    pg_locks.pid,
    pg_stat_activity.usename,
    pg_stat_activity.query,
    pg_locks.mode,
    pg_locks.granted,
    pg_stat_activity.query_start,
    age(clock_timestamp(), pg_stat_activity.query_start) AS query_age,
    pg_locks.locktype,
    pg_locks.relation::regclass AS locked_table
FROM pg_locks
JOIN pg_stat_activity ON pg_locks.pid = pg_stat_activity.pid
WHERE pg_locks.relation IS NOT NULL
  AND pg_stat_activity.query NOT LIKE '%pg_locks%'
ORDER BY query_start;

-- 8. Database growth tracking
CREATE OR REPLACE VIEW v_database_growth AS
SELECT
    current_database() as database,
    pg_database_size(current_database()) as size_bytes,
    pg_size_pretty(pg_database_size(current_database())) as size_pretty,
    (SELECT count(*) FROM pg_stat_user_tables) as table_count,
    (SELECT count(*) FROM pg_stat_user_indexes) as index_count,
    (SELECT sum(n_live_tup) FROM pg_stat_user_tables) as total_rows
;

-- 9. Query performance by table
CREATE OR REPLACE VIEW v_table_io_stats AS
SELECT
    schemaname,
    tablename,
    seq_scan as sequential_scans,
    seq_tup_read as seq_tuples_read,
    idx_scan as index_scans,
    idx_tup_fetch as index_tuples_fetched,
    n_tup_ins as rows_inserted,
    n_tup_upd as rows_updated,
    n_tup_del as rows_deleted,
    n_tup_hot_upd as hot_updates,
    CASE WHEN seq_scan + idx_scan > 0
         THEN round(100.0 * idx_scan / (seq_scan + idx_scan), 2)
         ELSE 0
    END as index_usage_percent
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;

-- 10. Active queries monitor
CREATE OR REPLACE VIEW v_active_queries AS
SELECT
    pid,
    usename as username,
    application_name,
    client_addr,
    backend_start,
    xact_start as transaction_start,
    query_start,
    state_change,
    wait_event_type,
    wait_event,
    state,
    backend_xid as transaction_id,
    backend_xmin as xmin,
    LEFT(query, 200) as query_preview,
    age(clock_timestamp(), query_start) AS query_duration
FROM pg_stat_activity
WHERE state != 'idle'
  AND pid != pg_backend_pid()
ORDER BY query_start;

-- Helper function to kill long-running queries
CREATE OR REPLACE FUNCTION kill_long_queries(duration_minutes INTEGER DEFAULT 60)
RETURNS TABLE(killed_pid INTEGER, username TEXT, duration INTERVAL, query TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pg_terminate_backend(pid),
        usename::TEXT,
        age(clock_timestamp(), query_start),
        LEFT(query, 100)::TEXT
    FROM pg_stat_activity
    WHERE state != 'idle'
      AND query NOT LIKE '%pg_stat_activity%'
      AND age(clock_timestamp(), query_start) > make_interval(mins => duration_minutes)
      AND pid != pg_backend_pid();
END;
$$ LANGUAGE plpgsql;

-- Usage examples:
-- SELECT * FROM v_table_stats;
-- SELECT * FROM v_unused_indexes;
-- SELECT * FROM v_maintenance_needs WHERE vacuum_status = 'NEEDS VACUUM';
-- SELECT * FROM v_active_queries WHERE query_duration > interval '5 minutes';
-- SELECT * FROM kill_long_queries(30); -- Kill queries running longer than 30 minutes