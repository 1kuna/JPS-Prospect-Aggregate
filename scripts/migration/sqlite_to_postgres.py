#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
Handles complete data migration with validation
"""

import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
import json
from pathlib import Path
import argparse
from typing import Dict, List, Tuple, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
from loguru import logger

# Configure Loguru for migration logging
logger.remove()
logger.add(
    "migration.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}",
    rotation="10 MB"
)
logger.add(
    sys.stdout,
    level="INFO", 
    format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}"
)

class DatabaseMigrator:
    def __init__(self, sqlite_path: str, postgres_url: str):
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        self.error_count = 0
        self.warning_count = 0
        
    def connect_sqlite(self) -> sqlite3.Connection:
        """Create SQLite connection with row factory"""
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def connect_postgres(self) -> psycopg2.connection:
        """Create PostgreSQL connection"""
        return psycopg2.connect(self.postgres_url)
    
    def migrate_business_database(self) -> bool:
        """Migrate business database from SQLite to PostgreSQL"""
        logger.info("Starting business database migration")
        logger.info(f"Source: {self.sqlite_path}")
        logger.info(f"Target: {self.postgres_url.split('@')[1]}")  # Hide password
        
        sqlite_conn = None
        pg_conn = None
        
        try:
            # Connect to both databases
            sqlite_conn = self.connect_sqlite()
            pg_conn = self.connect_postgres()
            pg_cursor = pg_conn.cursor()
            
            # Get migration order (respecting foreign key constraints)
            migration_order = [
                ('data_sources', self._migrate_data_sources),
                ('prospects', self._migrate_prospects),
                ('scraper_status', self._migrate_scraper_status),
                ('decisions', self._migrate_decisions),
            ]
            
            # Migrate each table
            for table_name, migration_func in migration_order:
                logger.info(f"\nMigrating {table_name} table...")
                
                try:
                    migration_func(sqlite_conn, pg_cursor)
                    pg_conn.commit()
                except Exception as e:
                    pg_conn.rollback()
                    logger.error(f"Failed to migrate {table_name}: {e}")
                    self.error_count += 1
                    raise
            
            # Update sequences
            self._update_sequences(pg_cursor)
            pg_conn.commit()
            
            logger.info("\n" + "="*50)
            logger.info("Business database migration completed")
            logger.info(f"Errors: {self.error_count}, Warnings: {self.warning_count}")
            
            return self.error_count == 0
            
        except Exception as e:
            if pg_conn:
                pg_conn.rollback()
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            if sqlite_conn:
                sqlite_conn.close()
            if pg_conn:
                pg_conn.close()
    
    def migrate_user_database(self) -> bool:
        """Migrate user database from SQLite to PostgreSQL"""
        logger.info("Starting user database migration")
        logger.info(f"Source: {self.sqlite_path}")
        logger.info(f"Target: {self.postgres_url.split('@')[1]}")  # Hide password
        
        sqlite_conn = None
        pg_conn = None
        
        try:
            sqlite_conn = self.connect_sqlite()
            pg_conn = self.connect_postgres()
            pg_cursor = pg_conn.cursor()
            
            # Migrate users table
            self._migrate_users(sqlite_conn, pg_cursor)
            pg_conn.commit()
            
            # Migrate user_settings table if it exists
            if self._table_exists(sqlite_conn, 'user_settings'):
                self._migrate_user_settings(sqlite_conn, pg_cursor)
                pg_conn.commit()
            
            # Update sequences
            self._update_user_sequences(pg_cursor)
            pg_conn.commit()
            
            logger.info("\n" + "="*50)
            logger.info("User database migration completed")
            logger.info(f"Errors: {self.error_count}, Warnings: {self.warning_count}")
            
            return self.error_count == 0
            
        except Exception as e:
            if pg_conn:
                pg_conn.rollback()
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            if sqlite_conn:
                sqlite_conn.close()
            if pg_conn:
                pg_conn.close()
    
    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Check if table exists in SQLite"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone() is not None
    
    def _migrate_data_sources(self, sqlite_conn: sqlite3.Connection, pg_cursor):
        """Migrate data_sources table"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM data_sources")
        rows = cursor.fetchall()
        
        insert_sql = '''
            INSERT INTO data_sources (id, name, url, active, created_at, updated_at, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                url = EXCLUDED.url,
                active = EXCLUDED.active,
                updated_at = EXCLUDED.updated_at,
                description = EXCLUDED.description
        '''
        
        batch_data = []
        for row in rows:
            batch_data.append((
                row['id'], row['name'], row['url'], 
                bool(row['active']), row['created_at'], 
                row['updated_at'], row['description']
            ))
        
        execute_batch(pg_cursor, insert_sql, batch_data, page_size=100)
        logger.info(f"  ✓ Migrated {len(batch_data)} data sources")
    
    def _migrate_prospects(self, sqlite_conn: sqlite3.Connection, pg_cursor):
        """Special handling for prospects table due to JSON fields"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM prospects")
        total_count = cursor.fetchone()[0]
        logger.info(f"  Found {total_count} prospects to migrate")
        
        # Process in batches to handle large datasets
        batch_size = 1000
        offset = 0
        total_migrated = 0
        
        insert_sql = '''
            INSERT INTO prospects (
                id, title, url, agency, office, location, type, naics, 
                response_date, set_aside, award_type, description, 
                contact_email, contact_phone, contact_name, archive_date,
                active, file_url, posted_date, source_id, file_name,
                dollar_value, is_duplicated, master_prospect_id,
                duplicate_confidence, duplicate_reason, has_file,
                llm_processed, llm_title, llm_value, llm_contact_email,
                llm_contact_name, llm_confidence_scores, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            ) ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                url = EXCLUDED.url,
                agency = EXCLUDED.agency,
                updated_at = EXCLUDED.updated_at
        '''
        
        while offset < total_count:
            cursor.execute(f"""
                SELECT * FROM prospects 
                ORDER BY id 
                LIMIT {batch_size} OFFSET {offset}
            """)
            rows = cursor.fetchall()
            
            if not rows:
                break
            
            batch_data = []
            for row in rows:
                try:
                    # Handle JSON fields
                    confidence_scores = row['llm_confidence_scores']
                    if confidence_scores:
                        if isinstance(confidence_scores, str):
                            try:
                                confidence_scores = json.loads(confidence_scores)
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON in llm_confidence_scores for prospect {row['id']}")
                                confidence_scores = None
                    
                    # Convert boolean fields
                    batch_data.append((
                        row['id'], row['title'], row['url'], row['agency'], row['office'],
                        row['location'], row['type'], row['naics'], row['response_date'],
                        row['set_aside'], row['award_type'], row['description'],
                        row['contact_email'], row['contact_phone'], row['contact_name'],
                        row['archive_date'], bool(row['active']), row['file_url'],
                        row['posted_date'], row['source_id'], row['file_name'],
                        row['dollar_value'], bool(row['is_duplicated']), 
                        row['master_prospect_id'], row['duplicate_confidence'],
                        row['duplicate_reason'], bool(row['has_file']),
                        bool(row['llm_processed']), row['llm_title'], row['llm_value'],
                        row['llm_contact_email'], row['llm_contact_name'],
                        json.dumps(confidence_scores) if confidence_scores else None,
                        row['created_at'], row['updated_at']
                    ))
                except Exception as e:
                    logger.error(f"Error processing prospect {row['id']}: {e}")
                    self.error_count += 1
            
            if batch_data:
                execute_batch(pg_cursor, insert_sql, batch_data, page_size=100)
                total_migrated += len(batch_data)
                logger.info(f"  Progress: {total_migrated}/{total_count} prospects migrated")
            
            offset += batch_size
        
        logger.info(f"  ✓ Migrated {total_migrated} prospects")
    
    def _migrate_scraper_status(self, sqlite_conn: sqlite3.Connection, pg_cursor):
        """Migrate scraper_status table"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM scraper_status")
        rows = cursor.fetchall()
        
        insert_sql = '''
            INSERT INTO scraper_status (
                id, source_name, status, last_run, records_found, 
                error_message, created_at, updated_at, duration_seconds
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                last_run = EXCLUDED.last_run,
                records_found = EXCLUDED.records_found,
                error_message = EXCLUDED.error_message,
                updated_at = EXCLUDED.updated_at,
                duration_seconds = EXCLUDED.duration_seconds
        '''
        
        batch_data = []
        for row in rows:
            batch_data.append((
                row['id'], row['source_name'], row['status'], row['last_run'],
                row['records_found'], row['error_message'], row['created_at'],
                row['updated_at'], row['duration_seconds']
            ))
        
        execute_batch(pg_cursor, insert_sql, batch_data, page_size=100)
        logger.info(f"  ✓ Migrated {len(batch_data)} scraper status records")
    
    def _migrate_decisions(self, sqlite_conn: sqlite3.Connection, pg_cursor):
        """Migrate decisions table"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM decisions")
        rows = cursor.fetchall()
        
        insert_sql = '''
            INSERT INTO decisions (
                id, prospect_id, user_id, decision, reasoning, 
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                decision = EXCLUDED.decision,
                reasoning = EXCLUDED.reasoning,
                updated_at = EXCLUDED.updated_at
        '''
        
        batch_data = []
        for row in rows:
            batch_data.append((
                row['id'], row['prospect_id'], row['user_id'],
                row['decision'], row['reasoning'],
                row['created_at'], row['updated_at']
            ))
        
        execute_batch(pg_cursor, insert_sql, batch_data, page_size=100)
        logger.info(f"  ✓ Migrated {len(batch_data)} decisions")
    
    def _migrate_users(self, sqlite_conn: sqlite3.Connection, pg_cursor):
        """Migrate users table"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        
        insert_sql = '''
            INSERT INTO users (
                id, username, email, full_name, password_hash, 
                is_admin, is_active, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                username = EXCLUDED.username,
                email = EXCLUDED.email,
                full_name = EXCLUDED.full_name,
                password_hash = EXCLUDED.password_hash,
                is_admin = EXCLUDED.is_admin,
                is_active = EXCLUDED.is_active,
                updated_at = EXCLUDED.updated_at
        '''
        
        batch_data = []
        for row in rows:
            batch_data.append((
                row['id'], row['username'], row['email'], row['full_name'],
                row['password_hash'], bool(row['is_admin']), 
                bool(row['is_active']), row['created_at'], row['updated_at']
            ))
        
        execute_batch(pg_cursor, insert_sql, batch_data, page_size=100)
        logger.info(f"  ✓ Migrated {len(batch_data)} users")
    
    def _migrate_user_settings(self, sqlite_conn: sqlite3.Connection, pg_cursor):
        """Migrate user_settings table"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM user_settings")
        rows = cursor.fetchall()
        
        insert_sql = '''
            INSERT INTO user_settings (
                id, user_id, key, value, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = EXCLUDED.updated_at
        '''
        
        batch_data = []
        for row in rows:
            batch_data.append((
                row['id'], row['user_id'], row['key'], row['value'],
                row['created_at'], row['updated_at']
            ))
        
        execute_batch(pg_cursor, insert_sql, batch_data, page_size=100)
        logger.info(f"  ✓ Migrated {len(batch_data)} user settings")
    
    def _update_sequences(self, pg_cursor):
        """Update PostgreSQL sequences to match SQLite auto-increment values"""
        sequences = [
            ('prospects_id_seq', 'prospects'),
            ('data_sources_id_seq', 'data_sources'),
            ('scraper_status_id_seq', 'scraper_status'),
            ('decisions_id_seq', 'decisions')
        ]
        
        logger.info("\nUpdating sequences...")
        for seq_name, table_name in sequences:
            try:
                pg_cursor.execute(f"""
                    SELECT setval('{seq_name}', 
                        COALESCE((SELECT MAX(id) FROM {table_name}), 1)
                    )
                """)
                pg_cursor.execute(f"SELECT last_value FROM {seq_name}")
                last_value = pg_cursor.fetchone()[0]
                logger.info(f"  ✓ Set {seq_name} to {last_value}")
            except Exception as e:
                logger.warning(f"  ⚠ Could not update {seq_name}: {e}")
                self.warning_count += 1
    
    def _update_user_sequences(self, pg_cursor):
        """Update PostgreSQL sequences for user database"""
        sequences = [
            ('users_id_seq', 'users'),
            ('user_settings_id_seq', 'user_settings')
        ]
        
        logger.info("\nUpdating user sequences...")
        for seq_name, table_name in sequences:
            try:
                # Check if table exists first
                pg_cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    )
                """, (table_name,))
                
                if pg_cursor.fetchone()[0]:
                    pg_cursor.execute(f"""
                        SELECT setval('{seq_name}', 
                            COALESCE((SELECT MAX(id) FROM {table_name}), 1)
                        )
                    """)
                    pg_cursor.execute(f"SELECT last_value FROM {seq_name}")
                    last_value = pg_cursor.fetchone()[0]
                    logger.info(f"  ✓ Set {seq_name} to {last_value}")
            except Exception as e:
                logger.warning(f"  ⚠ Could not update {seq_name}: {e}")
                self.warning_count += 1
    
    def verify_migration(self) -> bool:
        """Verify data integrity after migration"""
        logger.info("\n" + "="*50)
        logger.info("Verifying migration integrity...")
        
        sqlite_conn = None
        pg_conn = None
        
        try:
            sqlite_conn = self.connect_sqlite()
            pg_conn = self.connect_postgres()
            pg_cursor = pg_conn.cursor()
            
            # Determine which tables to check based on database type
            if 'jps_aggregate' in self.sqlite_path:
                tables = ['prospects', 'data_sources', 'scraper_status', 'decisions']
            else:
                tables = ['users']
                if self._table_exists(sqlite_conn, 'user_settings'):
                    tables.append('user_settings')
            
            all_valid = True
            
            for table in tables:
                # Count rows in SQLite
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                sqlite_count = sqlite_cursor.fetchone()[0]
                
                # Count rows in PostgreSQL
                pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                pg_count = pg_cursor.fetchone()[0]
                
                if sqlite_count == pg_count:
                    logger.info(f"  ✓ {table}: {sqlite_count} rows verified")
                else:
                    logger.error(f"  ✗ {table}: SQLite={sqlite_count}, PostgreSQL={pg_count}")
                    all_valid = False
                
                # Sample data verification (check first 10 rows)
                if table == 'prospects' and sqlite_count > 0:
                    sqlite_cursor.execute(f"""
                        SELECT id, title, agency, dollar_value 
                        FROM {table} 
                        ORDER BY id 
                        LIMIT 10
                    """)
                    sqlite_sample = sqlite_cursor.fetchall()
                    
                    for row in sqlite_sample:
                        pg_cursor.execute(f"""
                            SELECT title, agency, dollar_value 
                            FROM {table} 
                            WHERE id = %s
                        """, (row[0],))
                        pg_row = pg_cursor.fetchone()
                        
                        if not pg_row or row[1:] != pg_row:
                            logger.error(f"  ✗ Data mismatch in {table} id={row[0]}")
                            all_valid = False
                            break
            
            if all_valid:
                logger.info("\n✅ Migration verification completed successfully")
            else:
                logger.error("\n❌ Migration verification failed")
            
            return all_valid
            
        finally:
            if sqlite_conn:
                sqlite_conn.close()
            if pg_conn:
                pg_conn.close()


def main():
    """Main migration entry point"""
    parser = argparse.ArgumentParser(description='Migrate SQLite databases to PostgreSQL')
    parser.add_argument('--verify-only', action='store_true', 
                        help='Only verify existing migration without migrating')
    parser.add_argument('--business-only', action='store_true',
                        help='Only migrate business database')
    parser.add_argument('--users-only', action='store_true',
                        help='Only migrate users database')
    parser.add_argument('--env-file', default='.env.production',
                        help='Environment file to load (default: .env.production)')
    
    args = parser.parse_args()
    
    # Load environment
    if os.path.exists(args.env_file):
        load_dotenv(args.env_file)
    else:
        logging.error(f"Environment file not found: {args.env_file}")
        sys.exit(1)
    
    # Create backup directory
    backup_dir = Path('/opt/jps/backups/migration')
    if not backup_dir.exists():
        backup_dir = Path('backups/migration')  # Fallback for development
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Track overall success
    all_successful = True
    
    # Migrate business database
    if not args.users_only:
        if not args.verify_only:
            logging.info("Creating pre-migration backup of business database...")
            os.system(f"cp data/jps_aggregate.db {backup_dir}/jps_aggregate_pre_migration_{timestamp}.db")
        
        business_migrator = DatabaseMigrator(
            'data/jps_aggregate.db',
            os.getenv('DATABASE_URL')
        )
        
        if args.verify_only:
            if not business_migrator.verify_migration():
                all_successful = False
        else:
            if not business_migrator.migrate_business_database():
                all_successful = False
            elif not business_migrator.verify_migration():
                all_successful = False
    
    # Migrate user database
    if not args.business_only:
        if not args.verify_only:
            logging.info("\nCreating pre-migration backup of user database...")
            os.system(f"cp data/jps_users.db {backup_dir}/jps_users_pre_migration_{timestamp}.db")
        
        user_migrator = DatabaseMigrator(
            'data/jps_users.db',
            os.getenv('USER_DATABASE_URL')
        )
        
        if args.verify_only:
            if not user_migrator.verify_migration():
                all_successful = False
        else:
            if not user_migrator.migrate_user_database():
                all_successful = False
            elif not user_migrator.verify_migration():
                all_successful = False
    
    # Final summary
    print("\n" + "="*60)
    if all_successful:
        print("✅ Migration completed successfully!")
        if not args.verify_only:
            print(f"\nBackups saved to: {backup_dir}")
            print("\nNext steps:")
            print("1. Test the application with PostgreSQL")
            print("2. Run Alembic migrations: alembic upgrade head")
            print("3. Update application configuration to use PostgreSQL")
            print("4. Monitor for any issues")
    else:
        print("❌ Migration failed or verification errors found!")
        print("Check the migration.log file for details")
        sys.exit(1)


if __name__ == '__main__':
    main()