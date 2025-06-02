import logging
import pandas as pd
# from sqlalchemy.orm import Session # No longer needed directly
from sqlalchemy import insert # Changed to core SQLAlchemy insert
from sqlalchemy.exc import SQLAlchemyError
import numpy as np
import math

# from .models import Prospect # Old import
# from .session import get_db # Old import
from app.models import db, Prospect # Changed back to Prospect
from app.exceptions import ValidationError

# Logging is now handled by app.utils.logger (Loguru)

def paginate_sqlalchemy_query(query, page: int, per_page: int):
    """
    Paginates a SQLAlchemy query.

    Args:
        query: The SQLAlchemy query object.
        page (int): The current page number (1-indexed).
        per_page (int): The number of items per page.

    Returns:
        dict: A dictionary containing the paginated items and pagination details.
    
    Raises:
        ValidationError: If page or per_page have invalid values.
    """
    if not isinstance(page, int) or page < 1:
        raise ValidationError("Page number must be a positive integer greater than or equal to 1.")
    if not isinstance(per_page, int) or per_page < 1:
        raise ValidationError("Per_page must be a positive integer greater than or equal to 1.")
    if per_page > 100: # Example max limit
        raise ValidationError("Per_page cannot exceed 100.")

    try:
        total_items = query.count()
    except SQLAlchemyError as e:
        logging.error(f"Database error counting items for pagination: {e}", exc_info=True)
        # Depending on desired behavior, could re-raise, or return an error state
        raise # Re-raise to be handled by the caller or a global error handler

    if total_items == 0:
        total_pages = 0
        items = []
    else:
        total_pages = math.ceil(total_items / per_page)
        if page > total_pages and total_items > 0 : # If page is out of bounds but there are items
            raise ValidationError(f"Page number {page} is out of bounds. Total pages: {total_pages}.")
            
        offset = (page - 1) * per_page
        try:
            items_query = query.offset(offset).limit(per_page)
            items = items_query.all()
        except SQLAlchemyError as e:
            logging.error(f"Database error fetching paginated items: {e}", exc_info=True)
            # Depending on desired behavior, could re-raise, or return an error state
            raise # Re-raise

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1 and total_items > 0 # Ensure has_prev is false if no items
    }

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
        # For SQLite, we need to use a different approach since on_conflict_do_update is PostgreSQL-specific
        # We'll do a simple approach: delete existing records and insert new ones
        
        # Extract all IDs from the data to insert
        ids_to_upsert = [record['id'] for record in data_to_insert if 'id' in record]
        
        if ids_to_upsert:
            # Delete existing records with these IDs in batches to avoid SQLite limitations
            batch_size = 500  # SQLite has a limit on number of parameters
            for i in range(0, len(ids_to_upsert), batch_size):
                batch_ids = ids_to_upsert[i:i + batch_size]
                delete_count = session.query(Prospect).filter(Prospect.id.in_(batch_ids)).delete(synchronize_session=False)
                logging.info(f"Deleted {delete_count} existing records from batch {i//batch_size + 1}")
            # Commit all delete operations
            session.commit()
            logging.info(f"Deleted all existing records with matching IDs")
        
        # Insert all records in batches to avoid memory issues
        batch_size = 1000
        total_inserted = 0
        for i in range(0, len(data_to_insert), batch_size):
            batch_data = data_to_insert[i:i + batch_size]
            session.bulk_insert_mappings(Prospect, batch_data)
            total_inserted += len(batch_data)
            logging.info(f"Inserted batch {i//batch_size + 1}: {len(batch_data)} records")
        
        session.commit()
        logging.info(f"Successfully upserted {total_inserted} records into prospects table.")

    except SQLAlchemyError as e:
        logging.error(f"Database error during bulk upsert: {e}", exc_info=True)
        session.rollback()
    except Exception as e:
        logging.error(f"An unexpected error occurred during bulk upsert: {e}", exc_info=True)
        session.rollback()

# The old get_prospects_paginated function has been removed.
# Trailing comments and artifacts from previous attempts are also cleaned up.