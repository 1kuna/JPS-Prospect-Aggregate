import logging
import pandas as pd
# from sqlalchemy.orm import Session # No longer needed directly
from sqlalchemy import insert # Changed to core SQLAlchemy insert
from sqlalchemy.exc import SQLAlchemyError
import numpy as np
import datetime

# from .models import Prospect # Old import
# from .session import get_db # Old import
from app.models import db, Prospect # Changed back to Prospect

# Logging is now handled by app.utils.logger (Loguru)

def bulk_upsert_prospects(df_in: pd.DataFrame): # Renamed back
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
    # Assuming 'release_date' and 'award_date' are the correct date columns for Prospect
    date_columns = ['release_date', 'award_date'] # Adjusted from solicitation_date if necessary
    for col in date_columns:
        if col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].apply(lambda x: x.date() if pd.notna(x) else None)
                logging.debug(f"Converted column '{col}' to Python date objects.")
            else:
                logging.warning(f"Column '{col}' exists but is not datetime type ({df[col].dtype}). Attempting conversion.")
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
                except Exception as e:
                    logging.error(f"Failed to convert column '{col}' to date: {e}")
                    # Decide how to handle: skip column, fill with None, or raise error
                    df[col] = None # Example: fill with None
    # --- End Date Conversion ---

    try:
        df = df.fillna(value=np.nan).replace([np.nan], [None])
        df = df.infer_objects(copy=False)
        logging.debug("DataFrame NaN/null values replaced with None using fillna/replace.")
    except ImportError:
        logging.error("Numpy not found. Cannot perform robust NaN replacement. Falling back to df.where().")
        df = df.where(pd.notna(df), None)

    if 'loaded_at' in df.columns:
        df = df.drop(columns=['loaded_at'])
        
    data_to_insert = df.to_dict(orient='records')

    if not data_to_insert:
        logging.warning("Converted data to insert is empty.")
        return

    session = db.session # Use Flask-SQLAlchemy session directly

    try:
        # Prepare the insert statement using the Prospect table
        # Make sure Prospect.__table__ is correctly accessed after db setup
        stmt = insert(Prospect.__table__).values(data_to_insert)

        update_columns = { 
            col.name: col 
            for col in stmt.excluded 
            if col.name not in ['id', 'loaded_at']
        }
        
        on_conflict_stmt = stmt.on_conflict_do_update(
            index_elements=['id'], # Assuming 'id' is the primary key and conflict target
            set_=update_columns
        )

        session.execute(on_conflict_stmt)
        session.commit()
        logging.info(f"Successfully upserted {len(data_to_insert)} records into prospects table.")

    except SQLAlchemyError as e:
        logging.error(f"Database error during bulk upsert: {e}", exc_info=True)
        session.rollback()
    except Exception as e:
        logging.error(f"An unexpected error occurred during bulk upsert: {e}", exc_info=True)
        session.rollback() 