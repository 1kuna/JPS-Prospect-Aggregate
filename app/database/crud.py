import math

import numpy as np
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from app.database import db
from app.database.models import Prospect  # Changed back to Prospect
from app.exceptions import ValidationError
from app.utils.logger import logger


def paginate_sqlalchemy_query(query, page: int, per_page: int):
    """Paginates a SQLAlchemy query.

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
        raise ValidationError(
            "Page number must be a positive integer greater than or equal to 1."
        )
    if not isinstance(per_page, int) or per_page < 1:
        raise ValidationError(
            "Per_page must be a positive integer greater than or equal to 1."
        )
    if per_page > 100:  # Example max limit
        raise ValidationError("Per_page cannot exceed 100.")

    try:
        total_items = query.count()
    except SQLAlchemyError as e:
        logger.exception(f"Database error counting items for pagination: {e}")
        # Depending on desired behavior, could re-raise, or return an error state
        raise  # Re-raise to be handled by the caller or a global error handler

    if total_items == 0:
        total_pages = 0
        items = []
    else:
        total_pages = math.ceil(total_items / per_page)
        if (
            page > total_pages and total_items > 0
        ):  # If page is out of bounds but there are items
            raise ValidationError(
                f"Page number {page} is out of bounds. Total pages: {total_pages}."
            )

        offset = (page - 1) * per_page
        try:
            items_query = query.offset(offset).limit(per_page)
            items = items_query.all()
        except SQLAlchemyError as e:
            logger.exception(f"Database error fetching paginated items: {e}")
            # Depending on desired behavior, could re-raise, or return an error state
            raise  # Re-raise

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
        and total_items > 0,  # Ensure has_prev is false if no items
    }


def _preprocess_dataframe(df_in):
    """Preprocess DataFrame: convert dates, handle nulls, remove loaded_at column."""
    # Work on a copy to avoid SettingWithCopyWarning
    df = df_in.copy()

    # Convert Timestamp columns to Python date objects for SQLite compatibility
    date_columns = ["release_date", "award_date"]
    for col in date_columns:
        if col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].apply(lambda x: x.date() if pd.notna(x) else None)
                logger.debug(f"Converted column '{col}' to Python date objects.")
            else:
                logger.debug(
                    f"Column '{col}' is not datetime type ({df[col].dtype}). Attempting conversion."
                )
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
                    logger.debug(
                        f"Successfully converted column '{col}' to date objects."
                    )
                except Exception as e:
                    logger.error(f"Failed to convert column '{col}' to date: {e}")
                    df[col] = None

    # Handle NaN/null values
    try:
        with pd.option_context("future.no_silent_downcasting", True):
            df = df.fillna(value=np.nan).replace([np.nan], [None])
        df = df.infer_objects(copy=False)
        logger.debug(
            "DataFrame NaN/null values replaced with None using fillna/replace."
        )
    except ImportError:
        logger.error(
            "Numpy not found. Cannot perform robust NaN replacement. Falling back to df.where()."
        )
        df = df.where(pd.notna(df), None)

    if "loaded_at" in df.columns:
        df = df.drop(columns=["loaded_at"])

    return df


def bulk_upsert_prospects(
    df_in: pd.DataFrame,
    preserve_ai_data: bool = True,
    enable_smart_matching: bool = False,
):
    """Performs a bulk UPSERT (INSERT ON CONFLICT DO UPDATE) of prospect data
    from a Pandas DataFrame into the prospects table.

    This is now a thin wrapper that delegates to the enhanced_bulk_upsert_prospects
    function which handles all the complex logic including batch processing,
    AI field preservation, and smart duplicate matching.

    Args:
        df_in (pd.DataFrame): DataFrame containing prospect data matching the
                           Prospect model schema.
        preserve_ai_data (bool): If True, preserves AI-enhanced fields for
                               existing records that have been LLM-processed.
        enable_smart_matching (bool): If True, uses advanced matching strategies
                                    to prevent duplicates when titles/descriptions change.

    Returns:
        dict: Statistics about the upsert operation including processed, matched,
              inserted, duplicates_prevented, and ai_preserved counts.
    """
    if df_in.empty:
        logger.info("DataFrame is empty, skipping database insertion.")
        return {
            "processed": 0,
            "matched": 0,
            "inserted": 0,
            "duplicates_prevented": 0,
            "ai_preserved": 0,
        }

    # Preprocess the DataFrame
    df = _preprocess_dataframe(df_in)

    # Import here to avoid circular imports
    from app.utils.duplicate_prevention import enhanced_bulk_upsert_prospects

    # Delegate all work to the enhanced function
    stats = enhanced_bulk_upsert_prospects(
        df,
        session=db.session,
        source_id=None,  # Will be extracted from data
        preserve_ai_data=preserve_ai_data,
        enable_smart_matching=enable_smart_matching,
    )

    # Log results
    if stats["processed"] > 0:
        logger.info(
            f"Successfully processed {stats['processed']} records: "
            f"{stats['matched']} matched, {stats['inserted']} inserted"
        )
        if preserve_ai_data and stats["ai_preserved"] > 0:
            logger.info(
                f"AI-enhanced data preserved for {stats['ai_preserved']} records."
            )
        if enable_smart_matching and stats["duplicates_prevented"] > 0:
            logger.info(
                f"Smart matching prevented {stats['duplicates_prevented']} duplicates."
            )
    else:
        logger.warning("No records were processed.")

    return stats


def get_prospects_for_llm_enhancement(enhancement_type: str = "all", limit: int = None):
    """Get prospects that need LLM enhancement.

    Args:
        enhancement_type: Type of enhancement needed ('values', 'contacts', 'naics', 'all')
        limit: Maximum number of prospects to return

    Returns:
        List of Prospect objects needing enhancement
    """
    query = Prospect.query

    if enhancement_type == "values":
        # Prospects with value text but no parsed values
        query = query.filter(
            Prospect.estimated_value_text.isnot(None),
            Prospect.estimated_value_single.is_(None),
        )
    elif enhancement_type == "contacts":
        # Prospects with potential contact info in extra but no primary contact
        query = query.filter(
            Prospect.primary_contact_email.is_(None), Prospect.extra.isnot(None)
        )
    elif enhancement_type == "naics":
        # Prospects without NAICS codes
        query = query.filter(Prospect.naics.is_(None))
    elif enhancement_type == "all":
        # All prospects not yet processed by LLM
        query = query.filter(Prospect.ollama_processed_at.is_(None))
    else:
        raise ValidationError(f"Invalid enhancement type: {enhancement_type}")

    if limit:
        query = query.limit(limit)

    return query.all()


def update_prospect_llm_fields(prospect_id: str, llm_data: dict):
    """Update prospect with LLM-enhanced fields.

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
        "naics",
        "naics_description",
        "naics_source",
        "estimated_value_min",
        "estimated_value_max",
        "estimated_value_single",
        "primary_contact_email",
        "primary_contact_name",
        "ollama_processed_at",
        "ollama_model_version",
    ]

    for field in updateable_fields:
        if field in llm_data:
            setattr(prospect, field, llm_data[field])

    # Update extra field if provided
    if "extra_updates" in llm_data and prospect.extra:
        prospect.extra.update(llm_data["extra_updates"])
        # Flag the JSON field as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(prospect, "extra")

    try:
        db.session.commit()
        logger.info(f"Updated prospect {prospect_id} with LLM enhancements")
        return prospect
    except SQLAlchemyError as e:
        logger.error(f"Error updating prospect {prospect_id}: {e}")
        db.session.rollback()
        return None


def get_prospect_statistics():
    """Get statistics about prospects and their enhancement status.

    Returns:
        Dictionary with various statistics
    """
    try:
        stats = {
            "total_prospects": Prospect.query.count(),
            "with_naics": Prospect.query.filter(Prospect.naics.isnot(None)).count(),
            "with_naics_original": Prospect.query.filter(
                Prospect.naics_source == "original"
            ).count(),
            "with_naics_inferred": Prospect.query.filter(
                Prospect.naics_source == "llm_inferred"
            ).count(),
            "with_parsed_values": Prospect.query.filter(
                Prospect.estimated_value_single.isnot(None)
            ).count(),
            "with_contact_info": Prospect.query.filter(
                Prospect.primary_contact_email.isnot(None)
            ).count(),
            "llm_processed": Prospect.query.filter(
                Prospect.ollama_processed_at.isnot(None)
            ).count(),
            "pending_llm": Prospect.query.filter(
                Prospect.ollama_processed_at.is_(None)
            ).count(),
        }

        # Calculate percentages
        if stats["total_prospects"] > 0:
            stats["naics_coverage_pct"] = round(
                100 * stats["with_naics"] / stats["total_prospects"], 2
            )
            stats["value_parsing_pct"] = round(
                100 * stats["with_parsed_values"] / stats["total_prospects"], 2
            )
            stats["contact_extraction_pct"] = round(
                100 * stats["with_contact_info"] / stats["total_prospects"], 2
            )
            stats["llm_processed_pct"] = round(
                100 * stats["llm_processed"] / stats["total_prospects"], 2
            )
        else:
            stats["naics_coverage_pct"] = 0
            stats["value_parsing_pct"] = 0
            stats["contact_extraction_pct"] = 0
            stats["llm_processed_pct"] = 0

        return stats

    except SQLAlchemyError as e:
        logger.error(f"Error getting prospect statistics: {e}")
        return {}
