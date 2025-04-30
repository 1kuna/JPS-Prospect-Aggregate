import logging
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from .models import Prospect
from .session import get_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def bulk_upsert_prospects(df: pd.DataFrame):
    """
    Performs a bulk UPSERT (INSERT ON CONFLICT DO UPDATE) of prospect data 
    from a Pandas DataFrame into the prospects table.

    Args:
        df (pd.DataFrame): DataFrame containing prospect data matching the 
                           Prospect model schema.
    """
    if df.empty:
        logging.info("DataFrame is empty, skipping database insertion.")
        return

    # Convert DataFrame to list of dictionaries
    # Important: Ensure DataFrame columns match the Prospect model fields exactly
    # Handle NaN/NaT values appropriately for the database
    # Convert NaT to None for date/timestamp fields
    for col in df.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns:
        df[col] = df[col].apply(lambda x: x if pd.notna(x) else None)
    # Convert numeric NaN to None
    for col in df.select_dtypes(include=['number']).columns:
         df[col] = df[col].apply(lambda x: x if pd.notna(x) else None)
    # Convert object NaN/None to None
    for col in df.select_dtypes(include=['object']).columns:
         df[col] = df[col].apply(lambda x: x if pd.notna(x) else None)
         
    data_to_insert = df.to_dict(orient='records')

    if not data_to_insert:
        logging.warning("Converted data to insert is empty.")
        return

    with get_db() as db: # Use context manager for session handling
        if not db:
            logging.error("Failed to get database session. Aborting upsert.")
            return
            
        try:
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

            # Execute the bulk upsert
            db.execute(on_conflict_stmt)
            db.commit()
            logging.info(f"Successfully upserted {len(data_to_insert)} records.")

        except SQLAlchemyError as e:
            logging.error(f"Database error during bulk upsert: {e}", exc_info=True)
            db.rollback() # Rollback on error
        except Exception as e:
            logging.error(f"An unexpected error occurred during bulk upsert: {e}", exc_info=True)
            db.rollback()
            # Optionally re-raise if the calling function should handle it
            # raise 