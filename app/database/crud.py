import logging
import pandas as pd
# from sqlalchemy.orm import Session # No longer needed directly
from sqlalchemy import insert # Changed to core SQLAlchemy insert
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
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
                logging.debug(f"Column '{col}' is not datetime type ({df[col].dtype}). Attempting conversion.")
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
                    logging.debug(f"Successfully converted column '{col}' to date objects.")
                except Exception as e:
                    logging.error(f"Failed to convert column '{col}' to date: {e}")
                    # Decide how to handle: skip column, fill with None, or raise error
                    df[col] = None # Example: fill with None
    # --- End Date Conversion ---

    try:
        # Fix FutureWarning about downcasting on fillna
        with pd.option_context('future.no_silent_downcasting', True):
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

    # Remove duplicates within the data_to_insert itself
    seen_ids = set()
    unique_data_to_insert = []
    duplicates_count = 0
    
    for record in data_to_insert:
        record_id = record.get('id')
        if record_id and record_id not in seen_ids:
            seen_ids.add(record_id)
            unique_data_to_insert.append(record)
        elif record_id:
            duplicates_count += 1
    
    if duplicates_count > 0:
        logging.warning(f"Removed {duplicates_count} duplicate records within the same batch")
    
    data_to_insert = unique_data_to_insert

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
            try:
                session.bulk_insert_mappings(Prospect, batch_data)
                total_inserted += len(batch_data)
                logging.info(f"Inserted batch {i//batch_size + 1}: {len(batch_data)} records")
            except IntegrityError as ie:
                logging.error(f"IntegrityError in batch {i//batch_size + 1}: {ie}")
                # Try inserting records one by one to identify the problematic record
                session.rollback()
                successful_inserts = 0
                for record in batch_data:
                    try:
                        new_prospect = Prospect(**record)
                        session.add(new_prospect)
                        session.commit()
                        successful_inserts += 1
                    except IntegrityError:
                        session.rollback()
                        logging.debug(f"Skipping duplicate record with ID: {record.get('id', 'unknown')}")
                        continue
                total_inserted += successful_inserts
                logging.info(f"Inserted {successful_inserts}/{len(batch_data)} records individually from batch {i//batch_size + 1}")
        
        if total_inserted > 0:
            session.commit()
            logging.info(f"Successfully upserted {total_inserted} records into prospects table.")
        else:
            logging.warning("No records were inserted.")

    except SQLAlchemyError as e:
        logging.error(f"Database error during bulk upsert: {e}", exc_info=True)
        session.rollback()
    except Exception as e:
        logging.error(f"An unexpected error occurred during bulk upsert: {e}", exc_info=True)
        session.rollback()

# The old get_prospects_paginated function has been removed.
# Trailing comments and artifacts from previous attempts are also cleaned up.

def get_prospects_for_llm_enhancement(enhancement_type: str = 'all', limit: int = None):
    """
    Get prospects that need LLM enhancement.
    
    Args:
        enhancement_type: Type of enhancement needed ('values', 'contacts', 'naics', 'all')
        limit: Maximum number of prospects to return
        
    Returns:
        List of Prospect objects needing enhancement
    """
    query = Prospect.query
    
    if enhancement_type == 'values':
        # Prospects with value text but no parsed values
        query = query.filter(
            Prospect.estimated_value_text.isnot(None),
            Prospect.estimated_value_single.is_(None)
        )
    elif enhancement_type == 'contacts':
        # Prospects with potential contact info in extra but no primary contact
        query = query.filter(
            Prospect.primary_contact_email.is_(None),
            Prospect.extra.isnot(None)
        )
    elif enhancement_type == 'naics':
        # Prospects without NAICS codes
        query = query.filter(
            Prospect.naics.is_(None)
        )
    elif enhancement_type == 'all':
        # All prospects not yet processed by LLM
        query = query.filter(
            Prospect.ollama_processed_at.is_(None)
        )
    else:
        raise ValidationError(f"Invalid enhancement type: {enhancement_type}")
    
    if limit:
        query = query.limit(limit)
        
    return query.all()


def update_prospect_llm_fields(prospect_id: str, llm_data: dict):
    """
    Update prospect with LLM-enhanced fields.
    
    Args:
        prospect_id: The prospect ID to update
        llm_data: Dictionary containing LLM-enhanced fields
        
    Returns:
        Updated Prospect object or None if not found
    """
    prospect = Prospect.query.filter_by(id=prospect_id).first()
    
    if not prospect:
        return None
    
    # Update LLM-enhanced fields
    updateable_fields = [
        'naics', 'naics_description', 'naics_source',
        'estimated_value_min', 'estimated_value_max', 'estimated_value_single',
        'primary_contact_email', 'primary_contact_name',
        'ollama_processed_at', 'ollama_model_version'
    ]
    
    for field in updateable_fields:
        if field in llm_data:
            setattr(prospect, field, llm_data[field])
    
    # Update extra field if provided
    if 'extra_updates' in llm_data and prospect.extra:
        prospect.extra.update(llm_data['extra_updates'])
        # Flag the JSON field as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(prospect, 'extra')
    
    try:
        db.session.commit()
        logging.info(f"Updated prospect {prospect_id} with LLM enhancements")
        return prospect
    except SQLAlchemyError as e:
        logging.error(f"Error updating prospect {prospect_id}: {e}")
        db.session.rollback()
        return None


def get_prospect_statistics():
    """
    Get statistics about prospects and their enhancement status.
    
    Returns:
        Dictionary with various statistics
    """
    try:
        stats = {
            'total_prospects': Prospect.query.count(),
            'with_naics': Prospect.query.filter(Prospect.naics.isnot(None)).count(),
            'with_naics_original': Prospect.query.filter(Prospect.naics_source == 'original').count(),
            'with_naics_inferred': Prospect.query.filter(Prospect.naics_source == 'llm_inferred').count(),
            'with_parsed_values': Prospect.query.filter(Prospect.estimated_value_single.isnot(None)).count(),
            'with_contact_info': Prospect.query.filter(Prospect.primary_contact_email.isnot(None)).count(),
            'llm_processed': Prospect.query.filter(Prospect.ollama_processed_at.isnot(None)).count(),
            'pending_llm': Prospect.query.filter(Prospect.ollama_processed_at.is_(None)).count()
        }
        
        # Calculate percentages
        if stats['total_prospects'] > 0:
            stats['naics_coverage_pct'] = round(100 * stats['with_naics'] / stats['total_prospects'], 2)
            stats['value_parsing_pct'] = round(100 * stats['with_parsed_values'] / stats['total_prospects'], 2)
            stats['contact_extraction_pct'] = round(100 * stats['with_contact_info'] / stats['total_prospects'], 2)
            stats['llm_processed_pct'] = round(100 * stats['llm_processed'] / stats['total_prospects'], 2)
        else:
            stats['naics_coverage_pct'] = 0
            stats['value_parsing_pct'] = 0
            stats['contact_extraction_pct'] = 0
            stats['llm_processed_pct'] = 0
            
        return stats
        
    except SQLAlchemyError as e:
        logging.error(f"Error getting prospect statistics: {e}")
        return {}