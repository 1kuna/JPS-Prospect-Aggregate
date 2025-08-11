#!/usr/bin/env python
"""Create missing tables in SQLite database"""

import os
import sqlite3

# Get database path
db_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "jps_aggregate.db"
)

# SQL statements to create missing tables
create_tables_sql = [
    """
    CREATE TABLE IF NOT EXISTS prospects (
        id VARCHAR NOT NULL PRIMARY KEY,
        native_id VARCHAR,
        title TEXT,
        ai_enhanced_title TEXT,
        description TEXT,
        agency TEXT,
        naics VARCHAR,
        naics_description VARCHAR(200),
        naics_source VARCHAR(20),
        estimated_value REAL,
        est_value_unit VARCHAR,
        estimated_value_text VARCHAR(100),
        estimated_value_min REAL,
        estimated_value_max REAL,
        estimated_value_single REAL,
        release_date DATE,
        award_date DATE,
        award_fiscal_year INTEGER,
        place_city TEXT,
        place_state TEXT,
        place_country TEXT,
        contract_type TEXT,
        set_aside TEXT,
        set_aside_standardized VARCHAR(50),
        set_aside_standardized_label VARCHAR(100),
        primary_contact_email VARCHAR(100),
        primary_contact_name VARCHAR(100),
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        ollama_processed_at TIMESTAMP,
        ollama_model_version VARCHAR(50),
        enhancement_status VARCHAR(20),
        enhancement_started_at TIMESTAMP,
        enhancement_user_id INTEGER,
        extra TEXT,
        source_id INTEGER,
        FOREIGN KEY(source_id) REFERENCES data_sources (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS inferred_prospect_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prospect_id VARCHAR NOT NULL UNIQUE,
        inferred_naics TEXT,
        inferred_naics_description VARCHAR(200),
        inferred_estimated_value TEXT,
        inferred_est_value_unit TEXT,
        inferred_solicitation_date TEXT,
        inferred_award_date TEXT,
        inferred_place_city TEXT,
        inferred_place_state TEXT,
        inferred_place_country TEXT,
        inferred_contract_type TEXT,
        inferred_set_aside TEXT,
        inferred_primary_contact_email VARCHAR(100),
        inferred_primary_contact_name VARCHAR(100),
        llm_confidence_scores TEXT,
        inferred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        inferred_by_model VARCHAR,
        FOREIGN KEY(prospect_id) REFERENCES prospects (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scraper_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        status VARCHAR,
        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        details TEXT,
        FOREIGN KEY(source_id) REFERENCES data_sources (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS duplicate_prospects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_id VARCHAR NOT NULL,
        duplicate_id VARCHAR NOT NULL,
        confidence REAL,
        match_type VARCHAR,
        marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ai_data_preserved BOOLEAN DEFAULT 0,
        FOREIGN KEY(duplicate_id) REFERENCES prospects (id),
        FOREIGN KEY(original_id) REFERENCES prospects (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS file_processing_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name VARCHAR,
        file_path VARCHAR,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        row_count INTEGER,
        success BOOLEAN,
        error_message TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS go_no_go_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prospect_id VARCHAR NOT NULL,
        user_id INTEGER NOT NULL,
        decision VARCHAR(10) NOT NULL,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        FOREIGN KEY(prospect_id) REFERENCES prospects (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS llm_outputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        prospect_id VARCHAR NOT NULL,
        enhancement_type VARCHAR(50) NOT NULL,
        prompt TEXT NOT NULL,
        response TEXT,
        parsed_result TEXT,
        success BOOLEAN NOT NULL,
        error_message TEXT,
        processing_time REAL,
        FOREIGN KEY(prospect_id) REFERENCES prospects (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key VARCHAR(100) NOT NULL UNIQUE,
        value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    )
    """,
]

# Create indexes
create_indexes_sql = [
    # Prospects indexes
    "CREATE INDEX IF NOT EXISTS ix_prospects_agency ON prospects (agency)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_award_date ON prospects (award_date)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_award_fiscal_year ON prospects (award_fiscal_year)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_description ON prospects (description)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_enhancement_started_at ON prospects (enhancement_started_at)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_enhancement_status ON prospects (enhancement_status)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_enhancement_user_id ON prospects (enhancement_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_estimated_value_single ON prospects (estimated_value_single)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_loaded_at ON prospects (loaded_at)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_naics ON prospects (naics)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_naics_source ON prospects (naics_source)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_native_id ON prospects (native_id)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_ollama_processed_at ON prospects (ollama_processed_at)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_place_city ON prospects (place_city)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_place_state ON prospects (place_state)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_primary_contact_email ON prospects (primary_contact_email)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_release_date ON prospects (release_date)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_set_aside_standardized ON prospects (set_aside_standardized)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_source_id ON prospects (source_id)",
    "CREATE INDEX IF NOT EXISTS ix_prospects_title ON prospects (title)",
    # Other indexes
    "CREATE INDEX IF NOT EXISTS ix_scraper_status_last_checked ON scraper_status (last_checked)",
    "CREATE INDEX IF NOT EXISTS ix_scraper_status_source_id ON scraper_status (source_id)",
    "CREATE INDEX IF NOT EXISTS ix_scraper_status_status ON scraper_status (status)",
    "CREATE INDEX IF NOT EXISTS ix_duplicate_prospects_confidence ON duplicate_prospects (confidence)",
    "CREATE INDEX IF NOT EXISTS ix_duplicate_prospects_duplicate_id ON duplicate_prospects (duplicate_id)",
    "CREATE INDEX IF NOT EXISTS ix_duplicate_prospects_marked_at ON duplicate_prospects (marked_at)",
    "CREATE INDEX IF NOT EXISTS ix_duplicate_prospects_original_id ON duplicate_prospects (original_id)",
    "CREATE INDEX IF NOT EXISTS ix_go_no_go_decisions_created_at ON go_no_go_decisions (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_go_no_go_decisions_decision ON go_no_go_decisions (decision)",
    "CREATE INDEX IF NOT EXISTS ix_go_no_go_decisions_prospect_id ON go_no_go_decisions (prospect_id)",
    "CREATE INDEX IF NOT EXISTS ix_go_no_go_decisions_user_id ON go_no_go_decisions (user_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_prospect_unique ON go_no_go_decisions (user_id, prospect_id)",
    "CREATE INDEX IF NOT EXISTS ix_llm_outputs_enhancement_type ON llm_outputs (enhancement_type)",
    "CREATE INDEX IF NOT EXISTS ix_llm_outputs_prospect_id ON llm_outputs (prospect_id)",
    "CREATE INDEX IF NOT EXISTS ix_llm_outputs_success ON llm_outputs (success)",
    "CREATE INDEX IF NOT EXISTS ix_llm_outputs_timestamp ON llm_outputs (timestamp)",
]


def main():
    """Create missing tables in database"""
    print(f"Creating tables in database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create tables
        for sql in create_tables_sql:
            table_name = sql.split("CREATE TABLE IF NOT EXISTS ")[1].split(" ")[0]
            print(f"Creating table: {table_name}")
            cursor.execute(sql)

        # Create indexes
        print("\nCreating indexes...")
        for sql in create_indexes_sql:
            cursor.execute(sql)

        conn.commit()
        print("\nAll tables and indexes created successfully!")

        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("\nTables in database:")
        for table in tables:
            print(f"  - {table[0]}")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
