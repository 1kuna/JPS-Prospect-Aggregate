import json
import time
from datetime import timezone
UTC = timezone.utc
from datetime import datetime, timedelta

from flask import request
from sqlalchemy import func

from app.api.factory import api_route, create_blueprint, error_response, success_response
from app.database.models import (
    AIEnrichmentLog,
    LLMOutput,
    Prospect,
    db,
)
from app.services.enhancement_queue import add_individual_enhancement, enhancement_queue
from app.services.llm_service import llm_service

llm_bp, logger = create_blueprint("llm_api", "/api/llm")


@api_route(llm_bp, "/status", methods=["GET"], auth="admin")
def get_llm_status():
    """Get current LLM processing status and statistics"""
    # Get total prospects count
    total_prospects = db.session.query(func.count(Prospect.id)).scalar()

    # Get processed prospects count - only count those that have been fully processed
    # This counts prospects with ollama_processed_at timestamp, indicating complete AI processing
    processed_prospects = (
        db.session.query(func.count(Prospect.id))
        .filter(Prospect.ollama_processed_at.isnot(None))
        .scalar()
    )

    # Get NAICS coverage statistics
    naics_original = (
        db.session.query(func.count(Prospect.id))
        .filter(Prospect.naics.isnot(None), Prospect.naics_source == "original")
        .scalar()
    )

    naics_llm_inferred = (
        db.session.query(func.count(Prospect.id))
        .filter(Prospect.naics.isnot(None), Prospect.naics_source == "llm_inferred")
        .scalar()
    )

    total_with_naics = naics_original + naics_llm_inferred
    naics_coverage_percentage = (
        (total_with_naics / total_prospects * 100) if total_prospects > 0 else 0
    )

    # Get value parsing statistics
    value_parsed_count = (
        db.session.query(func.count(Prospect.id))
        .filter(Prospect.estimated_value_single.isnot(None))
        .scalar()
    )

    value_parsing_percentage = (
        (value_parsed_count / total_prospects * 100) if total_prospects > 0 else 0
    )

    # Get title enhancement statistics
    title_enhanced_count = (
        db.session.query(func.count(Prospect.id))
        .filter(Prospect.ai_enhanced_title.isnot(None))
        .scalar()
    )

    title_enhancement_percentage = (
        (title_enhanced_count / total_prospects * 100) if total_prospects > 0 else 0
    )

    # Get set-aside standardization statistics
    set_aside_standardized_count = (
        db.session.query(func.count(Prospect.id))
        .filter(Prospect.set_aside_standardized.isnot(None))
        .scalar()
    )

    set_aside_percentage = (
        (set_aside_standardized_count / total_prospects * 100)
        if total_prospects > 0
        else 0
    )

    # Get last processed timestamp and model version
    last_processed_prospect = (
        db.session.query(Prospect)
        .filter(Prospect.ollama_processed_at.isnot(None))
        .order_by(Prospect.ollama_processed_at.desc())
        .first()
    )

    last_processed = (
        last_processed_prospect.ollama_processed_at.isoformat() + "Z"
        if last_processed_prospect
        else None
    )
    model_version = (
        last_processed_prospect.ollama_model_version
        if last_processed_prospect
        else None
    )

    # Gather queue and LLM availability status for frontend
    try:
        queue_status = enhancement_queue.get_queue_status()
    except Exception:
        queue_status = {"is_processing": False, "total_items": 0}

    try:
        llm_status = llm_service.check_ollama_status()
    except Exception:
        llm_status = {"available": False, "error": "unavailable"}

    response_data = {
        "total_prospects": total_prospects,
        "processed_prospects": processed_prospects,
        "naics_coverage": {
            "original": naics_original,
            "llm_inferred": naics_llm_inferred,
            "total_percentage": round(naics_coverage_percentage, 1),
        },
        "value_parsing": {
            "parsed_count": value_parsed_count,
            "total_percentage": round(value_parsing_percentage, 1),
        },
        "title_enhancement": {
            "enhanced_count": title_enhanced_count,
            "total_percentage": round(title_enhancement_percentage, 1),
        },
        "set_aside_standardization": {
            "standardized_count": set_aside_standardized_count,
            "total_percentage": round(set_aside_percentage, 1),
        },
        "last_processed": last_processed,
        "model_version": model_version,
        "queue_status": queue_status,
        "llm_status": llm_status,
    }

    logger.info(
        f"Retrieved LLM status: {processed_prospects}/{total_prospects} fully processed"
    )
    return success_response(data=response_data)


@api_route(llm_bp, "/enhance", methods=["POST"], auth="admin")
def trigger_llm_enhancement():
    """Trigger LLM enhancement for prospects using Ollama and qwen3:8b"""
    data = request.get_json()
    if not data:
        return error_response("Request body required")

    enhancement_type = data.get("enhancement_type", "all")
    limit = data.get("limit", 10)  # Changed default from 100 to 10

    # Validate enhancement type
    valid_types = ["values", "naics", "naics_code", "naics_description", "titles", "set_asides", "all"]
    if enhancement_type not in valid_types:
        return error_response(f"Invalid enhancement type. Must be one of: {valid_types}")

    logger.info(f"Starting LLM enhancement: type={enhancement_type}, limit={limit}")
    start_time = time.time()

    # Initialize the LLM service
    from app.services.llm_service import ContractLLMService
    llm_service = ContractLLMService(model_name="qwen3:latest")

    # Get prospects that need processing
    prospects_query = Prospect.query.filter(Prospect.ollama_processed_at.is_(None))
    if limit:
        prospects_query = prospects_query.limit(limit)
    prospects = prospects_query.all()

    if not prospects:
        return success_response(
            message="No prospects found that need LLM enhancement",
            data={
                "processed_count": 0,
                "duration": 0.0,
                "enhancement_type": enhancement_type,
            }
        )

    # Run the appropriate enhancement
    if enhancement_type == "values":
        processed_count = llm_service.enhance_prospect_values(prospects)
    elif enhancement_type == "titles":
        processed_count = llm_service.enhance_prospect_titles(prospects)
    elif enhancement_type == "naics":
        processed_count = llm_service.enhance_prospect_naics(prospects)
    elif enhancement_type == "all":
        results = llm_service.enhance_all_prospects(limit=limit)
        processed_count = (
            results["titles_enhanced"]
            + results["values_enhanced"]
            + results["naics_enhanced"]
        )

    duration = time.time() - start_time

    response_data = {
        "message": "LLM enhancement completed successfully",
        "processed_count": processed_count,
        "duration": round(duration, 1),
        "enhancement_type": enhancement_type,
        "total_available": len(prospects),
    }

    logger.info(
        f"LLM enhancement completed: processed {processed_count} prospects in {duration:.1f}s"
    )
    return success_response(data=response_data)


@api_route(llm_bp, "/preview", methods=["POST"], auth="login")
def preview_llm_enhancement():
    """Preview LLM enhancement for a single prospect without saving"""
    data = request.get_json()
    if not data:
        return error_response("Request body required")

    prospect_id = data.get("prospect_id")
    enhancement_types = data.get("enhancement_types", ["values", "naics", "titles"])

    if not prospect_id:
        return error_response("prospect_id is required")

    # Get the prospect
    prospect = Prospect.query.get(prospect_id)
    if not prospect:
        return error_response("Prospect not found", status_code=404)

    # Initialize the base LLM service for individual enhancement previews
    from app.services.llm_service import LLMService

    llm_service = LLMService(model_name="qwen3:latest")

    preview_enhancements = {}
    confidence_scores = {}

    # Generate actual LLM previews based on requested types
    if "values" in enhancement_types and prospect.estimated_value_text:
        parsed_value = llm_service.parse_contract_value_with_llm(
            prospect.estimated_value_text
        )
        if parsed_value["single"] is not None:
            preview_enhancements.update(
                {
                    "estimated_value_single": float(parsed_value["single"]),
                    "estimated_value_min": float(parsed_value["min"])
                    if parsed_value["min"]
                    else None,
                    "estimated_value_max": float(parsed_value["max"])
                    if parsed_value["max"]
                    else None,
                }
            )
            confidence_scores["values"] = (
                0.85  # Could be enhanced to return actual confidence
            )

    if "titles" in enhancement_types and prospect.title and prospect.description:
        enhanced_title = llm_service.enhance_title_with_llm(
            prospect.title, prospect.description, prospect.agency or ""
        )
        if enhanced_title["enhanced_title"]:
            preview_enhancements.update(
                {"ai_enhanced_title": enhanced_title["enhanced_title"]}
            )
            confidence_scores["titles"] = enhanced_title.get("confidence", 0.8)

    if (
        "naics" in enhancement_types
        and not prospect.naics
        and prospect.title
        and prospect.description
    ):
        classification = llm_service.classify_naics_with_llm(
            prospect.title, prospect.description
        )
        if classification["code"]:
            preview_enhancements.update(
                {
                    "naics": classification["code"],
                    "naics_description": classification["description"],
                    "naics_source": "llm_inferred",
                }
            )
            confidence_scores["naics"] = classification.get("confidence", 0.8)

    mock_preview = {
        "prospect_id": prospect_id,
        "original_data": {
            "title": prospect.title,
            "estimated_value_text": prospect.estimated_value_text,
            "naics": prospect.naics,
            "naics_source": prospect.naics_source,
        },
        "preview_enhancements": preview_enhancements,
        "confidence_scores": confidence_scores,
    }

    logger.info(f"Generated LLM preview for prospect {prospect_id}")
    return success_response(data=mock_preview)


@api_route(llm_bp, "/iterative/start", methods=["POST"], auth="admin")
def start_iterative_enhancement():
    """Start iterative one-by-one LLM enhancement"""
    data = request.get_json()
    if not data:
        return error_response("Request body required")

    enhancement_type = data.get("enhancement_type", "all")
    skip_existing = data.get("skip_existing", True)

    # Validate enhancement type
    valid_types = ["values", "naics", "naics_code", "naics_description", "titles", "set_asides", "all"]
    if enhancement_type not in valid_types:
        return error_response(f"Invalid enhancement type. Must be one of: {valid_types}")

    # Start enhancement (runs in background thread)
    result = llm_service.start_enhancement(enhancement_type, skip_existing)

    logger.info(
        f"Started iterative LLM enhancement: type={enhancement_type}, skip_existing={skip_existing}"
    )
    return success_response(data=result)


@api_route(llm_bp, "/iterative/stop", methods=["POST"], auth="admin")
def stop_iterative_enhancement():
    """Stop the current iterative enhancement process"""
    # Stop enhancement
    result = llm_service.stop_enhancement()

    logger.info("Stopped iterative LLM enhancement")
    return success_response(data=result)


@api_route(llm_bp, "/iterative/progress", methods=["GET"], auth="admin")
def get_iterative_progress():
    """Get current progress of iterative enhancement"""
    progress = llm_service.get_progress()

    # Calculate percentage if processing
    if progress["total"] > 0:
        progress["percentage"] = round(
            (progress["processed"] / progress["total"]) * 100, 1
        )
    else:
        progress["percentage"] = 0

    return success_response(data=progress)


@api_route(llm_bp, "/logs", methods=["GET"], auth="admin")
def get_enhancement_logs():
    """Get recent AI enrichment logs"""
    limit = request.args.get("limit", 20, type=int)

    logs = (
        AIEnrichmentLog.query.order_by(AIEnrichmentLog.timestamp.desc())
        .limit(limit)
        .all()
    )

    log_data = []
    for log in logs:
        log_data.append(
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "enhancement_type": log.enhancement_type,
                "status": log.status,
                "processed_count": log.processed_count,
                "duration": log.duration,
                "message": log.message,
                "error": log.error,
            }
        )

    return success_response(data=log_data)


@api_route(llm_bp, "/outputs", methods=["GET"], auth="admin")
def get_llm_outputs():
    """Get recent LLM outputs for display"""
    limit = request.args.get("limit", 50, type=int)
    enhancement_type = request.args.get("enhancement_type", None)

    query = LLMOutput.query

    if enhancement_type and enhancement_type != "all":
        query = query.filter(LLMOutput.enhancement_type == enhancement_type)

    outputs = query.order_by(LLMOutput.timestamp.desc()).limit(limit).all()

    output_data = []
    for output in outputs:
        output_data.append(output.to_dict())

    return success_response(data=output_data)


def _ensure_extra_is_dict(prospect):
    """Ensure prospect.extra is a dictionary, converting from JSON string if needed"""
    if not prospect.extra:
        prospect.extra = {}
    elif isinstance(prospect.extra, str):
        try:
            prospect.extra = json.loads(prospect.extra)
        except (json.JSONDecodeError, TypeError):
            prospect.extra = {}

    if not isinstance(prospect.extra, dict):
        prospect.extra = {}


def _process_value_enhancement(prospect, llm_service, force_redo):
    """Process value parsing enhancement for a prospect."""

    # Values enhancement starting

    value_to_parse = None

    # Check if we should process values
    should_process = force_redo or not prospect.estimated_value_single

    if should_process:
        if prospect.estimated_value_text:
            value_to_parse = prospect.estimated_value_text
        elif prospect.estimated_value:
            # Convert numeric value to text for LLM processing
            value_to_parse = str(prospect.estimated_value)

    if value_to_parse:
        parsed_value = llm_service.parse_contract_value_with_llm(
            value_to_parse, prospect_id=prospect.id
        )

        # Check if we have either a single value OR a range (min/max)
        has_single = parsed_value["single"] is not None
        has_range = parsed_value["min"] is not None and parsed_value["max"] is not None

        if has_single or has_range:
            try:
                # Safely convert to float with validation
                single_val = (
                    float(parsed_value["single"])
                    if parsed_value["single"] is not None
                    else None
                )
                min_val = (
                    float(parsed_value["min"])
                    if parsed_value["min"] is not None
                    else None
                )
                max_val = (
                    float(parsed_value["max"])
                    if parsed_value["max"] is not None
                    else None
                )

                # Update prospect with parsed values based on what we have
                if has_single:
                    # Single value - set only the single field
                    prospect.estimated_value_single = single_val
                    prospect.estimated_value_min = None
                    prospect.estimated_value_max = None
                elif has_range:
                    # Range value - set min/max, clear single
                    prospect.estimated_value_single = None
                    prospect.estimated_value_min = min_val
                    prospect.estimated_value_max = max_val

                # Store the text version if it didn't exist
                if not prospect.estimated_value_text:
                    prospect.estimated_value_text = value_to_parse

                # Commit to database immediately for real-time updates
                db.session.commit()

                # Values enhancement completed
                return True

            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to convert LLM parsed values to float for prospect {prospect.id}: {e}"
                )
                # Values enhancement failed
                return False
    else:
        # No data to process - emit skipped completion
        pass
        # Values enhancement skipped

    return False


def _process_naics_enhancement(prospect, llm_service, force_redo):
    """Process NAICS classification enhancement for a prospect."""
    # NAICS enhancement starting

    # CRITICAL: Source NAICS codes should NEVER be overwritten by AI
    # AI classification should ONLY run when there's no NAICS code at all
    should_classify = not prospect.naics  # Removed force_redo to preserve source data

    # Check if we should backfill description for existing NAICS code
    should_backfill = prospect.naics and not prospect.naics_description

    if should_backfill:
        # PRIORITY: Backfill description for existing source NAICS code
        from app.utils.naics_lookup import get_naics_description

        official_description = get_naics_description(prospect.naics)

        if official_description:
            prospect.naics_description = official_description

            # Add backfill tracking to extras
            _ensure_extra_is_dict(prospect)
            prospect.extra["naics_description_backfilled"] = {
                "backfilled_at": datetime.now(UTC).isoformat() + "Z",
                "backfilled_by": "individual_enhancement",
                "original_source": prospect.naics_source or "unknown",
            }

            # Commit to database immediately for real-time updates
            db.session.commit()

            # NAICS enhancement completed with backfilled description
            return True
        else:
            # NAICS code not in our lookup table
            # NAICS enhancement skipped - no description available
            return False

    elif prospect.description and should_classify:
        # Run AI classification ONLY for prospects without NAICS codes
        classification = llm_service.classify_naics_with_llm(
            title=prospect.title,
            description=prospect.description,
            prospect_id=prospect.id,
            agency=prospect.agency,
            contract_type=prospect.contract_type,
            set_aside=prospect.set_aside,
            estimated_value=prospect.estimated_value_text or prospect.estimated_value,
        )

        if classification["code"]:
            prospect.naics = classification["code"]
            prospect.naics_description = classification["description"]
            prospect.naics_source = "llm_inferred"

            # Add confidence and all codes to extras
            _ensure_extra_is_dict(prospect)

            prospect.extra["llm_classification"] = {
                "naics_confidence": classification["confidence"],
                "all_naics_codes": classification.get("all_codes", []),
                "model_used": llm_service.model_name,
                "classified_at": datetime.now(UTC).isoformat() + "Z",
            }

            # Commit to database immediately for real-time updates
            db.session.commit()

            # NAICS enhancement completed with classification
            return True
        else:
            # NAICS enhancement failed - no valid classification
            return False

    elif prospect.naics and prospect.naics_description or prospect.naics:
        pass
    else:
        pass

        # NAICS enhancement skipped

    return False


def _process_title_enhancement(prospect, llm_service, force_redo):
    """Process title enhancement for a prospect."""

    # Title enhancement starting

    if prospect.title and (force_redo or not prospect.ai_enhanced_title):

        try:
            enhanced_title = llm_service.enhance_title_with_llm(
                prospect.title,
                prospect.description or "",
                prospect.agency or "",
                prospect_id=prospect.id,
            )
        except Exception as e:
            logger.error(
                f"LLM service error for prospect {prospect.id}: {e}"
            )
            # Title enhancement failed - LLM service error
            return False

        if enhanced_title["enhanced_title"]:
            prospect.ai_enhanced_title = enhanced_title["enhanced_title"]

            # Add confidence and reasoning to extras
            _ensure_extra_is_dict(prospect)

            prospect.extra["llm_title_enhancement"] = {
                "confidence": enhanced_title["confidence"],
                "reasoning": enhanced_title.get("reasoning", ""),
                "original_title": prospect.title,
                "model_used": llm_service.model_name,
                "enhanced_at": datetime.now(UTC).isoformat() + "Z",
            }

            # Commit to database immediately for real-time updates
            db.session.commit()

            # Title enhancement completed
            return True
        else:
            # Title enhancement failed - no title generated
            return False
    else:
        # Not processing title - emit skipped completion
        if not prospect.title:
            reason = "No title available to enhance"
        else:
            reason = "Already has enhanced title"

        # Title enhancement skipped

    return False


def _process_set_aside_enhancement(prospect, llm_service, force_redo):
    """Process set aside standardization and enhancement for a prospect."""
    # Ensure extra field is properly loaded as dict
    if prospect.extra is None:
        prospect.extra = {}
    elif isinstance(prospect.extra, str):
        try:
            import json

            prospect.extra = json.loads(prospect.extra)
        except (json.JSONDecodeError, TypeError):
            prospect.extra = {}

    # Debug logging
    logger.info(
        f"Set-aside enhancement for prospect {prospect.id}: "
        f"set_aside='{prospect.set_aside}', "
        f"standardized='{prospect.set_aside_standardized}', "
        f"force_redo={force_redo}"
    )
    logger.info(
        f"Extra field type: {type(prospect.extra)}, "
        f"has original_small_business_program: {'original_small_business_program' in (prospect.extra or {})}"
    )

    # Set-aside enhancement starting

    # Check if we should process set asides using the new standardized fields
    should_process = force_redo or not prospect.set_aside_standardized
    logger.info(
        f"Should process: {should_process} (force_redo={force_redo}, has_standardized={bool(prospect.set_aside_standardized)})"
    )

    if should_process:
        # Get comprehensive set-aside data (handles DHS small_business_program, etc.)
        comprehensive_data = llm_service._get_comprehensive_set_aside_data(
            prospect.set_aside, prospect
        )
        logger.info(f"Comprehensive data: '{comprehensive_data}'")

        # Process if we have data OR if force_redo is True
        if comprehensive_data or force_redo:
            # Process set aside using the LLM service
            try:
                processed_count = llm_service.enhance_prospect_set_asides(
                    [prospect], force_redo=force_redo
                )

                if processed_count > 0:
                    # Refresh the prospect to get updated standardized data
                    db.session.refresh(prospect)

                    # Check if standardization was successful
                    if prospect.set_aside_standardized:
                        # Set-aside enhancement completed with standardized data
                        return True
                    else:
                        # Set-aside enhancement failed - no standardized data
                        return False
                else:
                    # Set-aside enhancement failed - processing error
                    return False

            except Exception as e:
                logger.error(
                    f"Error processing set aside for prospect {prospect.id}: {e}"
                )
                # Set-aside enhancement failed with exception
                return False
        else:
            # No comprehensive data available - emit skipped completion
            reason = "No set aside data available to process (and not forcing)"
            logger.warning(f"Skipping set-aside enhancement: {reason}")
            # Set-aside enhancement skipped - no data available
    else:
        # Not processing set aside - emit skipped completion
        reason = (
            "Already has standardized set aside data"
            if not force_redo
            else "Set aside processing not needed"
        )
        logger.info(f"Skipping set-aside enhancement: {reason}")

        # Set-aside enhancement skipped

    return False


def _finalize_enhancement(prospect, llm_service, processed, enhancements, force_redo):
    """Finalize the enhancement process and return appropriate response."""
    # Always update timestamp for force_redo, even if no new enhancements
    if processed or force_redo:
        prospect.ollama_processed_at = datetime.now(UTC)
        prospect.ollama_model_version = llm_service.model_name
        db.session.commit()

        # Enhancement completed

        return success_response(
            message=f"Successfully enhanced prospect with: {', '.join(enhancements)}",
            data={
                "processed": True,
                "enhancements": enhancements,
            }
        )
    else:
        # Enhancement completed - no processing needed

        return success_response(
            message="Prospect already fully enhanced or no data to enhance",
            data={
                "processed": False,
                "enhancements": [],
            }
        )


@api_route(llm_bp, "/enhance-single", methods=["POST"], auth="login")
def enhance_single_prospect():
    """Enhance a single prospect with all AI enhancements using the priority queue system"""
    # Parse and validate request
    data = request.get_json()
    if not data:
        return error_response("Request body required")

    prospect_id = data.get("prospect_id")
    if not prospect_id:
        return error_response("prospect_id is required")

    force_redo = data.get("force_redo", False)
    user_id = data.get("user_id", 1)  # Default to 1 if no user provided

    # Handle both enhancement_type (string) and enhancement_types (array)
    enhancement_types = data.get("enhancement_types", None)
    if enhancement_types and isinstance(enhancement_types, list):
        # Convert array to comma-separated string
        enhancement_type = ",".join(enhancement_types)
    else:
        enhancement_type = data.get("enhancement_type", "all")

    # Get the prospect
    prospect = Prospect.query.get(prospect_id)
    if not prospect:
        return error_response("Prospect not found", status_code=404)

    # Check if prospect is already being enhanced by another user
    if prospect.enhancement_status == "in_progress":
        logger.info(
            f"Prospect {prospect_id} is in_progress: user_id={user_id}, enhancement_user_id={prospect.enhancement_user_id}"
        )
        if prospect.enhancement_user_id != user_id:
            logger.warning(
                f"User conflict for prospect {prospect_id}: requesting user={user_id}, locked by user={prospect.enhancement_user_id}"
            )
            return error_response(
                "Prospect is currently being enhanced by another user",
                status_code=409,
                data={
                    "status": "blocked",
                    "enhancement_status": "in_progress",
                    "enhancement_user_id": prospect.enhancement_user_id,
                }
            )

    # Also check if prospect is already in the queue with a different user
    # This prevents race conditions between queue processing and database locking
    existing_queue_items = [
        item
        for item in enhancement_queue._queue_items.values()
        if (
            str(item.prospect_id) == str(prospect_id)
            and item.type.value == "individual"
            and item.status.value in ["pending", "processing"]
        )
    ]

    if existing_queue_items:
        existing_item = existing_queue_items[0]
        if existing_item.user_id != user_id:
            return error_response(
                "Prospect is currently being enhanced by another user (queued)",
                status_code=409,
                data={
                    "status": "blocked",
                    "enhancement_status": "queued",
                    "queue_user_id": existing_item.user_id,
                }
            )
        else:
            # Same user, return existing queue item
            logger.info(
                f"Returning existing queue item {existing_item.id} for same user {user_id}"
            )
            return success_response(
                message=f"Enhancement request already queued for prospect {prospect_id}",
                data={
                    "status": "queued",
                    "queue_item_id": existing_item.id,
                    "prospect_id": prospect_id,
                    "priority": "high",
                    "was_existing": True,
                }
            )

    # Determine which steps will be skipped
    planned_steps = {}
    enhancement_types_list = enhancement_type.split(',') if enhancement_type else ['all']
    
    # Check each enhancement type to see if it will be skipped
    if 'all' in enhancement_types_list or 'titles' in enhancement_types_list:
        will_skip = bool(prospect.ai_enhanced_title) and not force_redo
        planned_steps['titles'] = {
            'will_process': not will_skip,
            'reason': 'already_enhanced' if will_skip else None
        }
    
    if 'all' in enhancement_types_list or 'values' in enhancement_types_list:
        will_skip = (bool(prospect.estimated_value_single) or 
                    bool(prospect.estimated_value_min) or 
                    bool(prospect.estimated_value_max)) and not force_redo
        planned_steps['values'] = {
            'will_process': not will_skip,
            'reason': 'already_parsed' if will_skip else None
        }
    
    if 'all' in enhancement_types_list or 'naics' in enhancement_types_list:
        will_skip = (bool(prospect.naics) and 
                    prospect.naics_source == 'llm_inferred') and not force_redo
        planned_steps['naics'] = {
            'will_process': not will_skip,
            'reason': 'already_classified' if will_skip else None
        }
    
    if 'naics_code' in enhancement_types_list:
        will_skip = bool(prospect.naics) and not force_redo
        planned_steps['naics_code'] = {
            'will_process': not will_skip,
            'reason': 'already_has_code' if will_skip else None
        }
    
    if 'naics_description' in enhancement_types_list:
        will_skip = bool(prospect.naics_description) and not force_redo
        planned_steps['naics_description'] = {
            'will_process': not will_skip,
            'reason': 'already_has_description' if will_skip else None
        }
    
    if 'all' in enhancement_types_list or 'set_asides' in enhancement_types_list:
        will_skip = bool(prospect.set_aside_standardized) and not force_redo
        planned_steps['set_asides'] = {
            'will_process': not will_skip,
            'reason': 'already_standardized' if will_skip else None
        }
    
    # Add to priority queue (returns dict with queue_item_id and was_existing)
    enhancement_result = add_individual_enhancement(
        prospect_id=prospect_id,
        enhancement_type=enhancement_type,
        user_id=user_id,
        force_redo=force_redo,
    )

    queue_item_id = enhancement_result["queue_item_id"]
    was_existing = enhancement_result["was_existing"]
    queue_position = enhancement_result.get("queue_position", 1)

    # Get queue status to provide better response information
    queue_status = enhancement_queue.get_queue_status()
    worker_running = queue_status.get("worker_running", False)

    logger.info(
        f"Added individual enhancement for prospect {prospect_id} to queue with ID {queue_item_id} (worker_running={worker_running}, position={queue_position})"
    )

    # Create appropriate message based on worker status
    if not worker_running:
        message = (
            f"Enhancement queued and worker auto-started for prospect {prospect_id}"
        )
    elif was_existing:
        message = (
            f"Enhancement request already in progress for prospect {prospect_id}"
        )
    else:
        message = f"Enhancement request queued for prospect {prospect_id}"

    return success_response(
        message=message,
        data={
            "status": "queued",
            "queue_item_id": queue_item_id,
            "prospect_id": prospect_id,
            "priority": "high",
            "was_existing": was_existing,
            "worker_running": worker_running,
            "queue_position": queue_position,
            "queue_size": queue_status.get("queue_size", 0),
            "planned_steps": planned_steps,  # Include planned steps for frontend
        }
    )


@api_route(llm_bp, "/cleanup-stale-locks", methods=["POST"], auth="admin")
def cleanup_stale_enhancement_locks():
    """Clean up enhancement locks that are older than 10 minutes"""
    # Calculate cutoff time (10 minutes ago)
    cutoff_time = datetime.now(UTC) - timedelta(minutes=10)

    # Find prospects with stale locks
    stale_prospects = (
        db.session.query(Prospect)
        .filter(
            Prospect.enhancement_status == "in_progress",
            Prospect.enhancement_started_at < cutoff_time,
        )
        .all()
    )

    cleanup_count = 0
    for prospect in stale_prospects:
        prospect.enhancement_status = "idle"
        prospect.enhancement_started_at = None
        prospect.enhancement_user_id = None
        cleanup_count += 1

    db.session.commit()

    logger.info(f"Cleaned up {cleanup_count} stale enhancement locks")
    return success_response(
        message=f"Cleaned up {cleanup_count} stale enhancement locks",
        data={"cleanup_count": cleanup_count}
    )


@api_route(llm_bp, "/queue/status", methods=["GET"], auth="admin")
def get_queue_status():
    """Get current enhancement queue status"""
    status = enhancement_queue.get_queue_status()
    return success_response(data=status)


@api_route(llm_bp, "/queue/item/<item_id>", methods=["GET"], auth="login")
def get_queue_item_status(item_id):
    """Get status of a specific queue item"""
    item_status = enhancement_queue.get_item_status(item_id)
    if not item_status:
        return error_response("Queue item not found", status_code=404)
    return success_response(data=item_status)


@api_route(llm_bp, "/queue/item/<item_id>/cancel", methods=["POST"], auth="login")
def cancel_queue_item(item_id):
    """Cancel a specific queue item"""
    success = enhancement_queue.cancel_item(item_id)
    if success:
        return success_response(message=f"Queue item {item_id} cancelled successfully")
    else:
        return error_response(
            "Cannot cancel item (not found or already processing)",
            status_code=400
        )


@api_route(llm_bp, "/queue/start-worker", methods=["POST"], auth="admin")
def start_queue_worker():
    """Start the enhancement queue worker"""
    enhancement_queue.start_worker()
    return success_response(message="Queue worker started successfully")


@api_route(llm_bp, "/queue/stop-worker", methods=["POST"], auth="admin")
def stop_queue_worker():
    """Stop the enhancement queue worker"""
    enhancement_queue.stop_worker()
    return success_response(message="Queue worker stopped successfully")


# SSE functionality has been removed - using polling instead


@api_route(llm_bp, "/enhancement-queue/<queue_item_id>", methods=["DELETE"], auth="login")
def cancel_enhancement(queue_item_id):
    """Cancel a queued enhancement request

    Regular users can only cancel their own enhancements.
    Admins and super admins can cancel any enhancement.
    """
    from flask import session

    # Get current user from session
    current_user_id = session.get("user_id")
    current_user_role = session.get("user_role", "user")

    # Check if the queue item exists and get its user_id
    queue_items = enhancement_queue._queue_items
    queue_item = queue_items.get(queue_item_id)

    if not queue_item:
        logger.warning(
            f"Failed to cancel enhancement queue item: {queue_item_id} (not found)"
        )
        return error_response(
            "Queue item not found",
            status_code=404,
            data={"success": False}
        )

    # Check ownership - regular users can only cancel their own enhancements
    if current_user_role not in ["admin", "super_admin"]:
        if hasattr(queue_item, 'user_id') and queue_item.user_id != current_user_id:
            logger.warning(
                f"User {current_user_id} attempted to cancel enhancement owned by user {queue_item.user_id}"
            )
            return error_response(
                "You can only cancel your own enhancement requests",
                status_code=403,
                data={"success": False}
            )

    # Attempt to cancel the queue item
    success = enhancement_queue.cancel_item(queue_item_id)

    if success:
        logger.info(
            f"Successfully cancelled enhancement queue item: {queue_item_id} by user {current_user_id}"
        )
        return success_response(
            message="Enhancement request cancelled successfully",
            data={"success": True}
        )
    else:
        logger.warning(
            f"Failed to cancel enhancement queue item: {queue_item_id} (already processing)"
        )
        return error_response(
            "Queue item is already processing and cannot be cancelled",
            status_code=409,
            data={"success": False}
        )
