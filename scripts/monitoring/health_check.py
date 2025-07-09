#!/usr/bin/env python3
"""
Database health check and monitoring script
Provides comprehensive health metrics for PostgreSQL databases
"""

import psycopg2
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseMonitor:
    def __init__(self, env_file: str = '.env.production'):
        """Initialize database monitor with environment configuration"""
        # Load environment
        if os.path.exists(env_file):
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self.business_url = os.getenv('DATABASE_URL')
        self.users_url = os.getenv('USER_DATABASE_URL')
        self.backup_dir = os.getenv('BACKUP_DIR', '/opt/jps/backups')
        
        # Thresholds for alerts
        self.thresholds = {
            'long_query_minutes': 5,
            'connection_usage_percent': 80,
            'dead_tuple_percent': 20,
            'cache_hit_ratio_min': 90,
            'disk_usage_percent': 85,
            'replication_lag_seconds': 300
        }
    
    def check_connection(self, db_url: str, db_name: str) -> Dict[str, Any]:
        """Check database connectivity and basic health"""
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Get version
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            # Get uptime
            cursor.execute("""
                SELECT current_timestamp - pg_postmaster_start_time() as uptime,
                       pg_postmaster_start_time() as start_time
            """)
            uptime_data = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                "status": "healthy",
                "database": db_name,
                "version": version.split('(')[0].strip(),
                "uptime": str(uptime_data[0]),
                "start_time": uptime_data[1].isoformat() if uptime_data[1] else None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "database": db_name,
                "error": str(e)
            }
    
    def check_database_size(self, db_url: str, db_name: str) -> Optional[Dict[str, Any]]:
        """Check database and table sizes"""
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Get database size
            cursor.execute("""
                SELECT 
                    pg_database_size(current_database()) as size_bytes,
                    pg_size_pretty(pg_database_size(current_database())) as size_pretty
            """)
            db_size = cursor.fetchone()
            
            # Get table sizes
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_total_relation_size(schemaname||'.'||tablename) as total_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size_pretty,
                    n_live_tup as row_count
                FROM pg_tables
                LEFT JOIN pg_stat_user_tables 
                    ON pg_tables.tablename = pg_stat_user_tables.relname
                WHERE schemaname = 'public'
                ORDER BY total_size DESC
                LIMIT 10
            """)
            
            tables = []
            for row in cursor.fetchall():
                tables.append({
                    "table": f"{row[0]}.{row[1]}",
                    "size_bytes": row[2],
                    "size_pretty": row[3],
                    "row_count": row[4] or 0
                })
            
            cursor.close()
            conn.close()
            
            return {
                "database": db_name,
                "size_bytes": db_size[0],
                "size_pretty": db_size[1],
                "largest_tables": tables
            }
        except Exception as e:
            logger.error(f"Failed to check size for {db_name}: {e}")
            return None
    
    def check_active_connections(self, db_url: str, db_name: str) -> Optional[Dict[str, Any]]:
        """Check active connections and connection pool usage"""
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Get connection stats
            cursor.execute("""
                SELECT 
                    count(*) as total,
                    count(*) FILTER (WHERE state = 'active') as active,
                    count(*) FILTER (WHERE state = 'idle') as idle,
                    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
                    count(*) FILTER (WHERE wait_event_type IS NOT NULL) as waiting
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND pid != pg_backend_pid()
            """)
            conn_stats = cursor.fetchone()
            
            # Get max connections setting
            cursor.execute("SHOW max_connections;")
            max_connections = int(cursor.fetchone()[0])
            
            # Get connections by application
            cursor.execute("""
                SELECT application_name, count(*) as count
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND application_name != ''
                GROUP BY application_name
                ORDER BY count DESC
            """)
            apps = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.close()
            conn.close()
            
            usage_percent = (conn_stats[0] / max_connections) * 100 if max_connections > 0 else 0
            
            result = {
                "database": db_name,
                "total_connections": conn_stats[0],
                "active_queries": conn_stats[1],
                "idle_connections": conn_stats[2],
                "idle_in_transaction": conn_stats[3],
                "waiting_connections": conn_stats[4],
                "max_connections": max_connections,
                "usage_percent": round(usage_percent, 2),
                "connections_by_app": apps
            }
            
            # Add warning if usage is high
            if usage_percent > self.thresholds['connection_usage_percent']:
                result["warning"] = f"Connection usage ({usage_percent:.1f}%) exceeds threshold ({self.thresholds['connection_usage_percent']}%)"
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check connections for {db_name}: {e}")
            return None
    
    def check_long_running_queries(self, db_url: str, db_name: str) -> Optional[List[Dict[str, Any]]]:
        """Check for long-running queries"""
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            threshold_minutes = self.thresholds['long_query_minutes']
            
            cursor.execute(f"""
                SELECT 
                    pid,
                    usename,
                    application_name,
                    client_addr,
                    query_start,
                    state,
                    wait_event_type,
                    wait_event,
                    EXTRACT(EPOCH FROM (now() - query_start)) as duration_seconds,
                    LEFT(query, 200) as query_preview
                FROM pg_stat_activity
                WHERE state != 'idle'
                  AND query NOT LIKE '%pg_stat_activity%'
                  AND now() - query_start > interval '{threshold_minutes} minutes'
                ORDER BY query_start
            """)
            
            queries = []
            for row in cursor.fetchall():
                queries.append({
                    "pid": row[0],
                    "user": row[1],
                    "application": row[2],
                    "client_addr": str(row[3]) if row[3] else "local",
                    "query_start": row[4].isoformat() if row[4] else None,
                    "state": row[5],
                    "wait_event": f"{row[6]}: {row[7]}" if row[6] else None,
                    "duration_seconds": int(row[8]),
                    "duration_pretty": str(timedelta(seconds=int(row[8]))),
                    "query": row[9]
                })
            
            cursor.close()
            conn.close()
            
            if queries:
                return {
                    "database": db_name,
                    "long_running_queries": queries,
                    "count": len(queries),
                    "threshold_minutes": threshold_minutes
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check queries for {db_name}: {e}")
            return None
    
    def check_table_health(self, db_url: str, db_name: str) -> Optional[Dict[str, Any]]:
        """Check table health metrics including bloat and maintenance needs"""
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Check for tables needing maintenance
            cursor.execute(f"""
                SELECT 
                    schemaname,
                    tablename,
                    n_dead_tup,
                    n_live_tup,
                    CASE WHEN n_live_tup > 0 
                         THEN round(100.0 * n_dead_tup / n_live_tup, 2)
                         ELSE 0
                    END AS dead_tuple_percent,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE n_live_tup > 1000
                  AND (n_dead_tup > 1000 OR 
                       (n_live_tup > 0 AND n_dead_tup::float / n_live_tup > {self.thresholds['dead_tuple_percent']} / 100.0))
                ORDER BY dead_tuple_percent DESC
            """)
            
            maintenance_needed = []
            for row in cursor.fetchall():
                maintenance_needed.append({
                    "table": f"{row[0]}.{row[1]}",
                    "dead_tuples": row[2],
                    "live_tuples": row[3],
                    "dead_tuple_percent": float(row[4]),
                    "last_vacuum": row[5].isoformat() if row[5] else None,
                    "last_autovacuum": row[6].isoformat() if row[6] else None,
                    "last_analyze": row[7].isoformat() if row[7] else None,
                    "last_autoanalyze": row[8].isoformat() if row[8] else None
                })
            
            # Check cache hit ratio
            cursor.execute("""
                SELECT 
                    sum(blks_hit) as cache_hits,
                    sum(blks_read) as disk_reads,
                    CASE WHEN sum(blks_hit) + sum(blks_read) > 0
                         THEN round(100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)), 2)
                         ELSE 0
                    END as cache_hit_ratio
                FROM pg_stat_database
                WHERE datname = current_database()
            """)
            cache_stats = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            result = {
                "database": db_name,
                "cache_hit_ratio": float(cache_stats[2]),
                "cache_hits": cache_stats[0],
                "disk_reads": cache_stats[1]
            }
            
            if maintenance_needed:
                result["tables_needing_maintenance"] = maintenance_needed
            
            # Add warning for low cache hit ratio
            if cache_stats[2] < self.thresholds['cache_hit_ratio_min']:
                result["warning"] = f"Cache hit ratio ({cache_stats[2]}%) below threshold ({self.thresholds['cache_hit_ratio_min']}%)"
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check table health for {db_name}: {e}")
            return None
    
    def check_backup_status(self) -> Dict[str, Any]:
        """Check backup status and recent backup files"""
        backup_status = {
            "backup_directory": self.backup_dir,
            "backups": {}
        }
        
        # Check if backup directory exists
        if not os.path.exists(self.backup_dir):
            backup_status["error"] = "Backup directory does not exist"
            return backup_status
        
        # Check each backup type
        for backup_type in ['daily', 'weekly', 'monthly']:
            type_dir = os.path.join(self.backup_dir, backup_type)
            if os.path.exists(type_dir):
                # Find latest backups
                backups = []
                for db_name in ['jps_aggregate', 'jps_users']:
                    pattern = f"{db_name}_{backup_type}_*.sql.gz"
                    files = sorted(
                        Path(type_dir).glob(pattern),
                        key=lambda x: x.stat().st_mtime,
                        reverse=True
                    )
                    
                    if files:
                        latest = files[0]
                        age_hours = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() / 3600
                        
                        backup_info = {
                            "database": db_name,
                            "file": latest.name,
                            "size": latest.stat().st_size,
                            "size_pretty": self._format_bytes(latest.stat().st_size),
                            "age_hours": round(age_hours, 1),
                            "timestamp": datetime.fromtimestamp(latest.stat().st_mtime).isoformat()
                        }
                        
                        # Add warning for old backups
                        if backup_type == 'daily' and age_hours > 26:
                            backup_info["warning"] = "Daily backup is more than 26 hours old"
                        
                        backups.append(backup_info)
                
                backup_status["backups"][backup_type] = backups
        
        return backup_status
    
    def _format_bytes(self, bytes: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} PB"
    
    def generate_health_report(self, output_format: str = 'json') -> Dict[str, Any]:
        """Generate comprehensive health report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "databases": {},
            "backups": {},
            "overall_status": "healthy",
            "warnings": [],
            "errors": []
        }
        
        # Check both databases
        for db_name, db_url in [("business", self.business_url), ("users", self.users_url)]:
            if not db_url:
                report["errors"].append(f"No connection URL configured for {db_name} database")
                continue
            
            db_report = {}
            
            # Connection health
            db_report["connection"] = self.check_connection(db_url, db_name)
            
            if db_report["connection"]["status"] == "healthy":
                # Size check
                size_info = self.check_database_size(db_url, db_name)
                if size_info:
                    db_report["size"] = size_info
                
                # Connection stats
                conn_info = self.check_active_connections(db_url, db_name)
                if conn_info:
                    db_report["connections"] = conn_info
                    if "warning" in conn_info:
                        report["warnings"].append(f"{db_name}: {conn_info['warning']}")
                
                # Long-running queries
                long_queries = self.check_long_running_queries(db_url, db_name)
                if long_queries:
                    db_report["long_queries"] = long_queries
                    report["warnings"].append(
                        f"{db_name}: {long_queries['count']} long-running queries found"
                    )
                
                # Table health
                table_health = self.check_table_health(db_url, db_name)
                if table_health:
                    db_report["table_health"] = table_health
                    if "warning" in table_health:
                        report["warnings"].append(f"{db_name}: {table_health['warning']}")
                    if "tables_needing_maintenance" in table_health:
                        report["warnings"].append(
                            f"{db_name}: {len(table_health['tables_needing_maintenance'])} tables need maintenance"
                        )
            else:
                report["errors"].append(f"{db_name}: {db_report['connection'].get('error', 'Unknown error')}")
                report["overall_status"] = "unhealthy"
            
            report["databases"][db_name] = db_report
        
        # Check backup status
        report["backups"] = self.check_backup_status()
        
        # Set overall status
        if report["errors"]:
            report["overall_status"] = "unhealthy"
        elif report["warnings"]:
            report["overall_status"] = "warning"
        
        return report
    
    def print_summary(self, report: Dict[str, Any]):
        """Print a human-readable summary of the health report"""
        # Status emoji
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️",
            "unhealthy": "❌"
        }
        
        print(f"\n{'='*60}")
        print(f"Database Health Report - {report['timestamp']}")
        print(f"{'='*60}")
        print(f"\nOverall Status: {status_emoji[report['overall_status']]} {report['overall_status'].upper()}")
        
        # Database status
        print("\n📊 Database Status:")
        for db_name, db_info in report["databases"].items():
            conn = db_info.get("connection", {})
            status = conn.get("status", "unknown")
            print(f"  {db_name.title()}: {status_emoji.get(status, '❓')} {status}")
            
            if status == "healthy":
                # Size info
                if "size" in db_info:
                    print(f"    Size: {db_info['size']['size_pretty']}")
                
                # Connection info
                if "connections" in db_info:
                    conn_info = db_info["connections"]
                    print(f"    Connections: {conn_info['total_connections']}/{conn_info['max_connections']} "
                          f"({conn_info['usage_percent']}%)")
                    print(f"    Active queries: {conn_info['active_queries']}")
                
                # Cache hit ratio
                if "table_health" in db_info:
                    print(f"    Cache hit ratio: {db_info['table_health']['cache_hit_ratio']}%")
        
        # Backup status
        print("\n💾 Backup Status:")
        backups = report.get("backups", {}).get("backups", {})
        for backup_type, backup_list in backups.items():
            if backup_list:
                latest = backup_list[0]  # Assuming sorted by recency
                status = "✅" if "warning" not in latest else "⚠️"
                print(f"  {backup_type.title()}: {status} {latest['age_hours']}h old, {latest['size_pretty']}")
        
        # Warnings
        if report["warnings"]:
            print(f"\n⚠️  Warnings ({len(report['warnings'])}):")
            for warning in report["warnings"][:5]:  # Show first 5
                print(f"  • {warning}")
            if len(report["warnings"]) > 5:
                print(f"  • ... and {len(report['warnings']) - 5} more")
        
        # Errors
        if report["errors"]:
            print(f"\n❌ Errors ({len(report['errors'])}):")
            for error in report["errors"]:
                print(f"  • {error}")
        
        print(f"\n{'='*60}\n")


def main():
    """Main health check entry point"""
    parser = argparse.ArgumentParser(description='Database health check and monitoring')
    parser.add_argument('--format', choices=['json', 'summary', 'both'], default='summary',
                        help='Output format (default: summary)')
    parser.add_argument('--output', help='Output file for JSON format')
    parser.add_argument('--env-file', default='.env.production',
                        help='Environment file to load (default: .env.production)')
    parser.add_argument('--check', choices=['connection', 'size', 'queries', 'all'], default='all',
                        help='Specific check to run (default: all)')
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = DatabaseMonitor(args.env_file)
    
    # Generate report
    report = monitor.generate_health_report()
    
    # Output based on format
    if args.format in ['json', 'both']:
        if args.output:
            # Save to file
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to: {args.output}")
        else:
            # Print to stdout
            print(json.dumps(report, indent=2))
    
    if args.format in ['summary', 'both']:
        monitor.print_summary(report)
    
    # Exit with appropriate code
    exit_code = 0
    if report["overall_status"] == "unhealthy":
        exit_code = 2
    elif report["overall_status"] == "warning":
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()