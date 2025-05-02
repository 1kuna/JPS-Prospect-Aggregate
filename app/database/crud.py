import logging
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
import numpy as np
import datetime # Import datetime

from .models import Prospect
from .session import get_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def bulk_upsert_prospects(df_in: pd.DataFrame):
    """
    Performs a bulk UPSERT (INSERT ON CONFLICT DO UPDATE) of prospect data 
    from a Pandas DataFrame into the prospects table.

    Args:
        df_in (pd.DataFrame): DataFrame containing prospect data matching the 
                           Prospect model schema.
    """
    if df_in.empty:
        logging.info("DataFrame is empty, skipping database insertion.")
        return

    # Work on a copy to avoid SettingWithCopyWarning
    df = df_in.copy()

    # --- Convert Timestamp columns to Python date objects for SQLite compatibility ---
    date_columns = ['award_date', 'solicitation_date']
    for col in date_columns:
        if col in df.columns:
            # Ensure the column is actually datetime first before using .dt accessor
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                # Convert NaT to None before converting to date object
                # Apply .dt.date only where the value is not NaT
                df[col] = df[col].apply(lambda x: x.date() if pd.notna(x) else None)
                logging.debug(f"Converted column '{col}' to Python date objects.")
            else:
                # If column exists but isn't datetime, try converting just in case
                # This might happen if data wasn't parsed correctly upstream
                logging.warning(f"Column '{col}' exists but is not datetime type ({df[col].dtype}). Attempting conversion.")
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    # --- End Date Conversion ---

    # --- Replace previous NaN handling with fillna/replace ---
    # Aggressively convert all forms of null/NaN to Python None
    # Fill pandas NA/NaT with numpy NaN first, then replace numpy NaN with None
    try:
        df = df.fillna(value=np.nan).replace([np.nan], [None])
        # Address FutureWarning by inferring object types after fillna/replace
        df = df.infer_objects(copy=False) 
        logging.debug("DataFrame NaN/null values replaced with None using fillna/replace.")
    except ImportError:
        logging.error("Numpy not found. Cannot perform robust NaN replacement. Falling back to df.where().")
        # Fallback if numpy isn't available (less robust)
        df = df.where(pd.notna(df), None)

    # Drop loaded_at column so the database default is used
    if 'loaded_at' in df.columns:
        df = df.drop(columns=['loaded_at'])
        
    data_to_insert = df.to_dict(orient='records')

    if not data_to_insert:
        logging.warning("Converted data to insert is empty.")
        return

    with get_db() as db:
        if not db:
            logging.error("Failed to get database session. Aborting upsert.")
            return

        try:
            # --- Debugging Logs --- REMOVED ---
            # log_limit = 3
            # logging.debug(f"--- Pre-Upsert Data Sample (First {log_limit} Records) ---")
            # for i, record in enumerate(data_to_insert[:log_limit]):
            #      est_val = record.get('estimated_value', 'MISSING_KEY')
            #      logging.debug(f"Record {i} estimated_value: {est_val} (Type: {type(est_val)})" )
            #      # Log the full record for detailed inspection
            #      logging.debug(f"Record {i} full data: {record}")
            # logging.debug("--- End Pre-Upsert Sample ---")
            # --- End Debugging Logs ---

            # Prepare the insert statement
            stmt = insert(Prospect.__table__).values(data_to_insert)

            # Define the conflict action (update specific columns on conflict)
            # Exclude primary key ('id') and 'loaded_at' from update
            update_columns = { 
                col.name: col 
                for col in stmt.excluded 
                if col.name not in ['id', 'loaded_at']
            }
            
            # ON CONFLICT DO UPDATE statement
            # index_elements=['id'] specifies the conflict target (primary key)
            on_conflict_stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=update_columns
            )

            # logging.debug("Executing upsert statement...") # Keep this DEBUG log?
            # Execute the bulk upsert
            db.execute(on_conflict_stmt)
            db.commit()
            logging.info(f"Successfully upserted {len(data_to_insert)} records.")

        except SQLAlchemyError as e:
            logging.error(f"Database error during bulk upsert: {e}", exc_info=True) # Keep original error log
            # --- Log data on error --- REMOVED ---
            # try:
            #     import json
            #     # Convert the list of dicts to a JSON string for easier logging
            #     data_as_json = json.dumps(data_to_insert, indent=1, default=str) # Use default=str for non-serializable types
            #     logging.error(f"Data causing SQLAlchemyError (potentially large):\n{data_as_json}")
            # except Exception as dump_error:
            #      logging.error(f"Could not dump data_to_insert as JSON: {dump_error}")
            #      logging.error(f"Data sample on error: {data_to_insert[:2]}") # Log a small sample instead
            # --- End log data on error ---
            db.rollback() # Rollback on error
        except Exception as e:
            logging.error(f"An unexpected error occurred during bulk upsert: {e}", exc_info=True) # Keep original error log
            # --- Log data on error --- REMOVED ---
            # try:
            #     import json
            #     data_as_json = json.dumps(data_to_insert, indent=1, default=str)
            #     logging.error(f"Data causing unexpected error (potentially large):\n{data_as_json}")
            # except Exception as dump_error:
            #      logging.error(f"Could not dump data_to_insert as JSON: {dump_error}")
            #      logging.error(f"Data sample on error: {data_to_insert[:2]}")
            # --- End log data on error ---
            db.rollback()
            # Optionally re-raise if the calling function should handle it
            # raise 