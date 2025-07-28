"""
Shared utilities for LLM services

This module contains common utility functions used by both batch and iterative
LLM processing services.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.database.models import Prospect
from app.utils.logger import logger


def ensure_extra_is_dict(prospect: Prospect) -> None:
    """
    Ensure prospect.extra is a dictionary.
    
    Handles cases where extra might be:
    - None
    - JSON string
    - Already a dictionary
    - Other types (converted to empty dict)
    
    Args:
        prospect: The prospect object to update
    """
    if not prospect.extra:
        prospect.extra = {}
    elif isinstance(prospect.extra, str):
        try:
            prospect.extra = json.loads(prospect.extra)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse extra field as JSON for prospect {prospect.id}, resetting to empty dict")
            prospect.extra = {}
    
    if not isinstance(prospect.extra, dict):
        logger.warning(f"Extra field is not a dict for prospect {prospect.id}, resetting to empty dict")
        prospect.extra = {}


def update_prospect_timestamps(prospect: Prospect, model_name: str) -> None:
    """
    Update prospect's ollama processing timestamps and model version.
    
    This is called after any LLM enhancement to track when the prospect
    was last processed and by which model.
    
    Args:
        prospect: The prospect object to update
        model_name: The name of the LLM model used for processing
    """
    try:
        prospect.ollama_processed_at = datetime.now(timezone.utc)
        prospect.ollama_model_version = model_name
    except Exception as e:
        logger.error(f"Failed to update prospect timestamps: {e}")


def emit_field_update(prospect_id: str, field_type: str, field_data: Dict[str, Any], 
                     emit_callback: Optional[callable] = None) -> None:
    """
    Emit a real-time field update event for a prospect.
    
    This is used to notify frontend clients of field updates during
    iterative processing.
    
    Args:
        prospect_id: The ID of the prospect being updated
        field_type: The type of field being updated (e.g., 'values', 'naics', 'titles')
        field_data: Dictionary containing the updated field values
        emit_callback: Optional callback function for emitting events
    """
    if not emit_callback:
        return
    
    try:
        emit_callback('field_update', {
            'prospect_id': prospect_id,
            'field_type': field_type,
            'fields': field_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to emit field update: {e}")


def calculate_progress_percentage(processed: int, total: int) -> float:
    """
    Calculate progress percentage safely.
    
    Args:
        processed: Number of items processed
        total: Total number of items
        
    Returns:
        Progress percentage (0-100)
    """
    if total <= 0:
        return 100.0
    return min(100.0, (processed / total) * 100)


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string like "2h 15m" or "45s"
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"


def get_enhancement_field_names(enhancement_type: str) -> Dict[str, list]:
    """
    Get the database field names affected by each enhancement type.
    
    Args:
        enhancement_type: Type of enhancement ('values', 'naics', 'titles', 'set_asides', 'all')
        
    Returns:
        Dictionary mapping enhancement types to field names
    """
    field_mapping = {
        'values': ['estimated_value_single', 'estimated_value_min', 'estimated_value_max', 'estimated_value_text'],
        'naics': ['naics', 'naics_description', 'naics_source'],
        'titles': ['ai_enhanced_title'],
        'set_asides': ['set_aside_standardized', 'set_aside_standardized_label']
    }
    
    if enhancement_type == 'all':
        # Flatten all field lists
        all_fields = []
        for fields in field_mapping.values():
            all_fields.extend(fields)
        return {'all': all_fields}
    
    return {enhancement_type: field_mapping.get(enhancement_type, [])}


def should_skip_prospect(prospect: Prospect, enhancement_type: str, skip_existing: bool = True) -> bool:
    """
    Determine if a prospect should be skipped for a given enhancement type.
    
    Args:
        prospect: The prospect to check
        enhancement_type: Type of enhancement to perform
        skip_existing: Whether to skip prospects that already have enhanced data
        
    Returns:
        True if prospect should be skipped, False otherwise
    """
    if not skip_existing:
        return False
    
    # Check based on enhancement type
    if enhancement_type == "values":
        # Skip if already has parsed value
        return prospect.estimated_value_single is not None
    
    elif enhancement_type == "naics":
        # Skip if already has LLM-inferred NAICS
        return prospect.naics is not None and prospect.naics_source == 'llm_inferred'
    
    elif enhancement_type == "titles":
        # Skip if already has enhanced title
        return prospect.ai_enhanced_title is not None
    
    elif enhancement_type == "set_asides":
        # Skip if already has standardized set-aside
        return prospect.set_aside_standardized is not None
    
    elif enhancement_type == "all":
        # For "all", skip if prospect has been processed at all
        return prospect.ollama_processed_at is not None
    
    return False


def create_enhancement_summary(results: Dict[str, bool]) -> Dict[str, Any]:
    """
    Create a summary of enhancement results.
    
    Args:
        results: Dictionary of enhancement results by type
        
    Returns:
        Summary dictionary with counts and success rate
    """
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    return {
        'total_attempted': total,
        'successful': successful,
        'failed': total - successful,
        'success_rate': (successful / total * 100) if total > 0 else 0,
        'details': results
    }