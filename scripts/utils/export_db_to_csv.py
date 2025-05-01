import sqlite3
import pandas as pd
from pathlib import Path
import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def export_db_tables():
    """Connects to the SQLite database and exports prospects, inferred data, and a merged view to CSV files."""
    try:
        # Determine project root directory (assuming script is in scripts/utils)
        project_root = Path(__file__).resolve().parents[2]
        db_path = project_root / 'data' / 'jps_aggregate.db'
        output_dir = project_root / 'data' / 'processed'
        output_prospects_path = output_dir / 'jps_prospects_export.csv'
        output_inferred_path = output_dir / 'jps_inferred_export.csv'
        output_merged_path = output_dir / 'jps_merged_export.csv'

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"Connecting to database: {db_path}")
        if not db_path.exists():
            logger.error(f"Database file not found at {db_path}")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # --- Export 1: Prospects Table --- 
        prospects_table_name = 'prospects'
        logger.info(f"Reading table '{prospects_table_name}'...")
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{prospects_table_name}';")
        if cursor.fetchone() is None:
            logger.error(f"Table '{prospects_table_name}' does not exist.")
        else:
            df_prospects = pd.read_sql_query(f"SELECT * FROM {prospects_table_name}", conn)
            logger.info(f"Read {len(df_prospects)} rows from '{prospects_table_name}'. Exporting...")
            df_prospects.to_csv(output_prospects_path, index=False, encoding='utf-8')
            logger.info(f"Successfully exported {prospects_table_name} to {output_prospects_path}")

        # --- Export 2: Inferred Data Table --- 
        inferred_table_name = 'inferred_prospect_data'
        logger.info(f"Reading table '{inferred_table_name}'...")
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{inferred_table_name}';")
        if cursor.fetchone() is None:
            logger.warning(f"Table '{inferred_table_name}' does not exist. Skipping export.")
            df_inferred = pd.DataFrame() # Create empty df for merge step
        else:
            df_inferred = pd.read_sql_query(f"SELECT * FROM {inferred_table_name}", conn)
            logger.info(f"Read {len(df_inferred)} rows from '{inferred_table_name}'. Exporting...")
            df_inferred.to_csv(output_inferred_path, index=False, encoding='utf-8')
            logger.info(f"Successfully exported {inferred_table_name} to {output_inferred_path}")

        # --- Export 3: Merged View --- 
        logger.info("Creating merged view (prospects LEFT JOIN inferred_prospect_data)...")
        
        # Use pandas merge for simplicity, ensure prospects df exists
        if 'df_prospects' in locals() and not df_prospects.empty:
            if not df_inferred.empty:
                # Perform left merge
                df_merged = pd.merge(df_prospects, df_inferred, left_on='id', right_on='prospect_id', how='left')
                # Optionally drop the redundant prospect_id from the inferred table
                if 'prospect_id' in df_merged.columns:
                     df_merged = df_merged.drop(columns=['prospect_id'])
            else:
                 logger.warning("Inferred data table is empty or does not exist, merged view will only contain prospects data.")
                 df_merged = df_prospects.copy() # Create a copy to avoid modifying original df

            logger.info(f"Created merged view with {len(df_merged)} rows. Exporting...")
            df_merged.to_csv(output_merged_path, index=False, encoding='utf-8')
            logger.info(f"Successfully exported merged view to {output_merged_path}")
        else:
             logger.error("Prospects DataFrame is empty or was not loaded. Cannot create merged view.")

        conn.close()
        logger.info("Database connection closed.")

    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
    except pd.errors.DatabaseError as e:
         logger.error(f"Pandas database error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    export_db_tables() 