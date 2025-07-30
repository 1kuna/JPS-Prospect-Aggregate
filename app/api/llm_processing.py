from flask import Blueprint, jsonify, request, Response, stream_with_context
from app.database.models import Prospect, db, AIEnrichmentLog, LLMOutput, InferredProspectData
from app.utils.logger import logger
from app.services.llm_service import llm_service
from app.services.enhancement_queue import enhancement_queue
from app.api.auth import admin_required
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import time
import asyncio
import json

llm_bp = Blueprint('llm_api', __name__, url_prefix='/api/llm')

@llm_bp.route('/status', methods=['GET'])
@admin_required
def get_llm_status():
    """Get current LLM processing status and statistics"""
    try:
        # Get total prospects count
        total_prospects = db.session.query(func.count(Prospect.id)).scalar()
        
        # Get processed prospects count - only count those that have been fully processed
        # This counts prospects with ollama_processed_at timestamp, indicating complete AI processing
        processed_prospects = db.session.query(func.count(Prospect.id)).filter(
            Prospect.ollama_processed_at.isnot(None)
        ).scalar()
        
        # Get NAICS coverage statistics
        naics_original = db.session.query(func.count(Prospect.id)).filter(
            Prospect.naics.isnot(None),
            Prospect.naics_source == 'original'
        ).scalar()
        
        naics_llm_inferred = db.session.query(func.count(Prospect.id)).filter(
            Prospect.naics.isnot(None),
            Prospect.naics_source == 'llm_inferred'
        ).scalar()
        
        total_with_naics = naics_original + naics_llm_inferred
        naics_coverage_percentage = (total_with_naics / total_prospects * 100) if total_prospects > 0 else 0
        
        # Get value parsing statistics
        value_parsed_count = db.session.query(func.count(Prospect.id)).filter(
            Prospect.estimated_value_single.isnot(None)
        ).scalar()
        
        value_parsing_percentage = (value_parsed_count / total_prospects * 100) if total_prospects > 0 else 0
        
        
        # Get title enhancement statistics
        title_enhanced_count = db.session.query(func.count(Prospect.id)).filter(
            Prospect.ai_enhanced_title.isnot(None)
        ).scalar()
        
        title_enhancement_percentage = (title_enhanced_count / total_prospects * 100) if total_prospects > 0 else 0
        
        # Get set-aside standardization statistics
        set_aside_standardized_count = db.session.query(func.count(Prospect.id)).filter(
            Prospect.set_aside_standardized.isnot(None)
        ).scalar()
        
        set_aside_percentage = (set_aside_standardized_count / total_prospects * 100) if total_prospects > 0 else 0
        
        # Get last processed timestamp and model version
        last_processed_prospect = db.session.query(Prospect).filter(
            Prospect.ollama_processed_at.isnot(None)
        ).order_by(Prospect.ollama_processed_at.desc()).first()
        
        last_processed = last_processed_prospect.ollama_processed_at.isoformat() if last_processed_prospect else None
        model_version = last_processed_prospect.ollama_model_version if last_processed_prospect else None
        
        response_data = {
            "total_prospects": total_prospects,
            "processed_prospects": processed_prospects,
            "naics_coverage": {
                "original": naics_original,
                "llm_inferred": naics_llm_inferred,
                "total_percentage": round(naics_coverage_percentage, 1)
            },
            "value_parsing": {
                "parsed_count": value_parsed_count,
                "total_percentage": round(value_parsing_percentage, 1)
            },
            "title_enhancement": {
                "enhanced_count": title_enhanced_count,
                "total_percentage": round(title_enhancement_percentage, 1)
            },
            "set_aside_standardization": {
                "standardized_count": set_aside_standardized_count,
                "total_percentage": round(set_aside_percentage, 1)
            },
            "last_processed": last_processed,
            "model_version": model_version
        }
        
        logger.info(f"Retrieved LLM status: {processed_prospects}/{total_prospects} fully processed")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting LLM status: {e}", exc_info=True)
        return jsonify({"error": "Failed to get LLM status"}), 500

@llm_bp.route('/enhance', methods=['POST'])
@admin_required
def trigger_llm_enhancement():
    """Trigger LLM enhancement for prospects using Ollama and qwen3:8b"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
            
        enhancement_type = data.get('enhancement_type', 'all')
        limit = data.get('limit', 10)  # Changed default from 100 to 10
        
        # Validate enhancement type
        valid_types = ['values', 'naics', 'titles', 'set_asides', 'all']
        if enhancement_type not in valid_types:
            return jsonify({"error": f"Invalid enhancement type. Must be one of: {valid_types}"}), 400
            
        logger.info(f"Starting LLM enhancement: type={enhancement_type}, limit={limit}")
        start_time = time.time()
        
        # Initialize the LLM service
        llm_service = ContractLLMService(model_name='qwen3:latest')
        
        # Get prospects that need processing
        prospects_query = Prospect.query.filter(Prospect.ollama_processed_at.is_(None))
        if limit:
            prospects_query = prospects_query.limit(limit)
        prospects = prospects_query.all()
        
        if not prospects:
            return jsonify({
                "message": "No prospects found that need LLM enhancement",
                "processed_count": 0,
                "duration": 0.0,
                "enhancement_type": enhancement_type
            }), 200
        
        # Run the appropriate enhancement
        if enhancement_type == 'values':
            processed_count = llm_service.enhance_prospect_values(prospects)
        elif enhancement_type == 'titles':
            processed_count = llm_service.enhance_prospect_titles(prospects)
        elif enhancement_type == 'naics':
            processed_count = llm_service.enhance_prospect_naics(prospects)
        elif enhancement_type == 'all':
            results = llm_service.enhance_all_prospects(limit=limit)
            processed_count = results['titles_enhanced'] + results['values_enhanced'] + results['naics_enhanced']
        
        duration = time.time() - start_time
        
        response_data = {
            "message": f"LLM enhancement completed successfully",
            "processed_count": processed_count,
            "duration": round(duration, 1),
            "enhancement_type": enhancement_type,
            "total_available": len(prospects)
        }
        
        logger.info(f"LLM enhancement completed: processed {processed_count} prospects in {duration:.1f}s")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error triggering LLM enhancement: {e}", exc_info=True)
        return jsonify({"error": f"Failed to trigger LLM enhancement: {str(e)}"}), 500

@llm_bp.route('/preview', methods=['POST'])
@admin_required
def preview_llm_enhancement():
    """Preview LLM enhancement for a single prospect without saving"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
            
        prospect_id = data.get('prospect_id')
        enhancement_types = data.get('enhancement_types', ['values', 'naics', 'titles'])
        
        if not prospect_id:
            return jsonify({"error": "prospect_id is required"}), 400
            
        # Get the prospect
        prospect = Prospect.query.get(prospect_id)
        if not prospect:
            return jsonify({"error": "Prospect not found"}), 404
            
        # Initialize the base LLM service for individual enhancement previews
        from app.services.llm_service import LLMService
        llm_service = LLMService(model_name='qwen3:latest')
        
        preview_enhancements = {}
        confidence_scores = {}
        
        # Generate actual LLM previews based on requested types
        if 'values' in enhancement_types and prospect.estimated_value_text:
            parsed_value = llm_service.parse_contract_value_with_llm(prospect.estimated_value_text)
            if parsed_value['single'] is not None:
                preview_enhancements.update({
                    'estimated_value_single': float(parsed_value['single']),
                    'estimated_value_min': float(parsed_value['min']) if parsed_value['min'] else None,
                    'estimated_value_max': float(parsed_value['max']) if parsed_value['max'] else None
                })
                confidence_scores['values'] = 0.85  # Could be enhanced to return actual confidence
        
        if 'titles' in enhancement_types and prospect.title and prospect.description:
            enhanced_title = llm_service.enhance_title_with_llm(
                prospect.title, 
                prospect.description,
                prospect.agency or ""
            )
            if enhanced_title['enhanced_title']:
                preview_enhancements.update({
                    'ai_enhanced_title': enhanced_title['enhanced_title']
                })
                confidence_scores['titles'] = enhanced_title.get('confidence', 0.8)
        
        if 'naics' in enhancement_types and not prospect.naics and prospect.title and prospect.description:
            classification = llm_service.classify_naics_with_llm(prospect.title, prospect.description)
            if classification['code']:
                preview_enhancements.update({
                    'naics': classification['code'],
                    'naics_description': classification['description'],
                    'naics_source': 'llm_inferred'
                })
                confidence_scores['naics'] = classification.get('confidence', 0.8)
        
        mock_preview = {
            "prospect_id": prospect_id,
            "original_data": {
                "title": prospect.title,
                "estimated_value_text": prospect.estimated_value_text,
                "naics": prospect.naics,
                "naics_source": prospect.naics_source
            },
            "preview_enhancements": preview_enhancements,
            "confidence_scores": confidence_scores
        }
        
        logger.info(f"Generated LLM preview for prospect {prospect_id}")
        return jsonify(mock_preview), 200
        
    except Exception as e:
        logger.error(f"Error generating LLM preview: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate LLM preview: {str(e)}"}), 500

@llm_bp.route('/iterative/start', methods=['POST'])
@admin_required
def start_iterative_enhancement():
    """Start iterative one-by-one LLM enhancement"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
            
        enhancement_type = data.get('enhancement_type', 'all')
        skip_existing = data.get('skip_existing', True)
        
        # Validate enhancement type
        valid_types = ['values', 'naics', 'titles', 'set_asides', 'all']
        if enhancement_type not in valid_types:
            return jsonify({"error": f"Invalid enhancement type. Must be one of: {valid_types}"}), 400
        
        # Start enhancement (runs in background thread)
        result = iterative_service.start_enhancement(enhancement_type, skip_existing)
        
        logger.info(f"Started iterative LLM enhancement: type={enhancement_type}, skip_existing={skip_existing}")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error starting iterative enhancement: {e}", exc_info=True)
        return jsonify({"error": f"Failed to start iterative enhancement: {str(e)}"}), 500

@llm_bp.route('/iterative/stop', methods=['POST'])
@admin_required
def stop_iterative_enhancement():
    """Stop the current iterative enhancement process"""
    try:
        # Stop enhancement
        result = iterative_service.stop_enhancement()
        
        logger.info("Stopped iterative LLM enhancement")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error stopping iterative enhancement: {e}", exc_info=True)
        return jsonify({"error": f"Failed to stop iterative enhancement: {str(e)}"}), 500

@llm_bp.route('/iterative/progress', methods=['GET'])
@admin_required
def get_iterative_progress():
    """Get current progress of iterative enhancement"""
    try:
        progress = iterative_service.get_progress()
        
        # Calculate percentage if processing
        if progress['total'] > 0:
            progress['percentage'] = round((progress['processed'] / progress['total']) * 100, 1)
        else:
            progress['percentage'] = 0
        
        return jsonify(progress), 200
        
    except Exception as e:
        logger.error(f"Error getting iterative progress: {e}", exc_info=True)
        return jsonify({"error": "Failed to get progress"}), 500

@llm_bp.route('/logs', methods=['GET'])
@admin_required
def get_enhancement_logs():
    """Get recent AI enrichment logs"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        logs = AIEnrichmentLog.query.order_by(
            AIEnrichmentLog.timestamp.desc()
        ).limit(limit).all()
        
        log_data = []
        for log in logs:
            log_data.append({
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "enhancement_type": log.enhancement_type,
                "status": log.status,
                "processed_count": log.processed_count,
                "duration": log.duration,
                "message": log.message,
                "error": log.error
            })
        
        return jsonify(log_data), 200
        
    except Exception as e:
        logger.error(f"Error getting enhancement logs: {e}", exc_info=True)
        return jsonify({"error": "Failed to get logs"}), 500

@llm_bp.route('/outputs', methods=['GET'])
@admin_required
def get_llm_outputs():
    """Get recent LLM outputs for display"""
    try:
        limit = request.args.get('limit', 50, type=int)
        enhancement_type = request.args.get('enhancement_type', None)
        
        query = LLMOutput.query
        
        if enhancement_type and enhancement_type != 'all':
            query = query.filter(LLMOutput.enhancement_type == enhancement_type)
        
        outputs = query.order_by(
            LLMOutput.timestamp.desc()
        ).limit(limit).all()
        
        output_data = []
        for output in outputs:
            output_data.append(output.to_dict())
        
        return jsonify(output_data), 200
        
    except Exception as e:
        logger.error(f"Error getting LLM outputs: {e}", exc_info=True)
        return jsonify({"error": "Failed to get outputs"}), 500

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
    logger.info(f"VALUE_ENHANCEMENT_DEBUG: Starting for prospect {prospect.id}")
    logger.info(f"VALUE_ENHANCEMENT_DEBUG: force_redo={force_redo}, has_existing_value={bool(prospect.estimated_value_single)}")
    
    # Always emit start event first
    emit_enhancement_progress(prospect.id, 'values_started', {
        'force_redo': force_redo,
        'has_existing_value': bool(prospect.estimated_value_single)
    })
    
    value_to_parse = None
    
    # Check if we should process values
    should_process = force_redo or not prospect.estimated_value_single
    logger.info(f"VALUE_ENHANCEMENT_DEBUG: should_process={should_process} for prospect {prospect.id}")
    
    if should_process:
        if prospect.estimated_value_text:
            value_to_parse = prospect.estimated_value_text
        elif prospect.estimated_value:
            # Convert numeric value to text for LLM processing
            value_to_parse = str(prospect.estimated_value)
    
    if value_to_parse:
        
        parsed_value = llm_service.parse_contract_value_with_llm(value_to_parse, prospect_id=prospect.id)
        
        # Check if we have either a single value OR a range (min/max)
        has_single = parsed_value['single'] is not None
        has_range = parsed_value['min'] is not None and parsed_value['max'] is not None
        
        if has_single or has_range:
            try:
                # Safely convert to float with validation
                single_val = float(parsed_value['single']) if parsed_value['single'] is not None else None
                min_val = float(parsed_value['min']) if parsed_value['min'] is not None else None
                max_val = float(parsed_value['max']) if parsed_value['max'] is not None else None
                
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
                
                # Emit completion event with new values
                emit_enhancement_progress(prospect.id, 'values_completed', {
                    'estimated_value_single': single_val,
                    'estimated_value_min': min_val,
                    'estimated_value_max': max_val,
                    'is_range': has_range and not has_single
                })
                return True
                
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to convert LLM parsed values to float for prospect {prospect.id}: {e}")
                emit_enhancement_progress(prospect.id, 'values_failed', {'error': str(e)})
                return False
    else:
        # No data to process - emit skipped completion
        reason = 'Already has parsed value' if not should_process else 'No value text available to parse'
        emit_enhancement_progress(prospect.id, 'values_completed', {
            'skipped': True,
            'reason': reason
        })
    
    return False


def _process_naics_enhancement(prospect, llm_service, force_redo):
    """Process NAICS classification enhancement for a prospect."""
    # Always emit start event first
    emit_enhancement_progress(prospect.id, 'naics_started', {
        'force_redo': force_redo,
        'has_existing_naics': bool(prospect.naics),
        'has_description': bool(prospect.description)
    })
    
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
            prospect.extra['naics_description_backfilled'] = {
                'backfilled_at': datetime.now(timezone.utc).isoformat(),
                'backfilled_by': 'individual_enhancement',
                'original_source': prospect.naics_source or 'unknown'
            }
            
            # Commit to database immediately for real-time updates
            db.session.commit()
            
            # Emit completion event with backfilled description
            emit_enhancement_progress(prospect.id, 'naics_completed', {
                'naics': prospect.naics,
                'naics_description': official_description,
                'naics_source': prospect.naics_source or 'unknown',
                'action': 'backfilled'
            })
            return True
        else:
            # NAICS code not in our lookup table
            emit_enhancement_progress(prospect.id, 'naics_completed', {
                'skipped': True,
                'reason': f'No description available for NAICS code {prospect.naics}'
            })
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
            estimated_value=prospect.estimated_value_text or prospect.estimated_value
        )
        
        if classification['code']:
            prospect.naics = classification['code']
            prospect.naics_description = classification['description']
            prospect.naics_source = 'llm_inferred'
            
            # Add confidence and all codes to extras
            _ensure_extra_is_dict(prospect)
                
            prospect.extra['llm_classification'] = {
                'naics_confidence': classification['confidence'],
                'all_naics_codes': classification.get('all_codes', []),
                'model_used': llm_service.model_name,
                'classified_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Commit to database immediately for real-time updates
            db.session.commit()
            
            # Emit completion event with new NAICS data
            emit_enhancement_progress(prospect.id, 'naics_completed', {
                'naics': classification['code'],
                'naics_description': classification['description'],
                'naics_source': 'llm_inferred',
                'confidence': classification['confidence'],
                'action': 'classified'
            })
            return True
        else:
            emit_enhancement_progress(prospect.id, 'naics_failed', {'error': 'No valid NAICS classification found'})
            return False
    
    else:
        # Not processing NAICS - emit skipped completion
        if prospect.naics and prospect.naics_description:
            reason = 'Already has NAICS code and description'
        elif prospect.naics:
            reason = 'Has NAICS code but no description available in lookup table'
        else:
            reason = 'No description available for AI classification'
        
        emit_enhancement_progress(prospect.id, 'naics_completed', {
            'skipped': True,
            'reason': reason
        })
    
    return False

def _process_title_enhancement(prospect, llm_service, force_redo):
    """Process title enhancement for a prospect."""
    logger.info(f"TITLE_ENHANCEMENT_DEBUG: Starting for prospect {prospect.id}")
    logger.info(f"TITLE_ENHANCEMENT_DEBUG: force_redo={force_redo}, has_title={bool(prospect.title)}, has_enhanced_title={bool(prospect.ai_enhanced_title)}")
    
    # Always emit start event first
    emit_enhancement_progress(prospect.id, 'titles_started', {
        'force_redo': force_redo,
        'has_existing_enhanced_title': bool(prospect.ai_enhanced_title),
        'has_title': bool(prospect.title)
    })
    
    if prospect.title and (force_redo or not prospect.ai_enhanced_title):
        logger.info(f"TITLE_ENHANCEMENT_DEBUG: Proceeding with LLM enhancement for prospect {prospect.id}")
        
        try:
            logger.info(f"TITLE_ENHANCEMENT_DEBUG: Calling LLM service for prospect {prospect.id}")
            enhanced_title = llm_service.enhance_title_with_llm(
                prospect.title, 
                prospect.description or "",
                prospect.agency or "",
                prospect_id=prospect.id
            )
            logger.info(f"TITLE_ENHANCEMENT_DEBUG: LLM response for prospect {prospect.id}: {enhanced_title}")
        except Exception as e:
            logger.error(f"TITLE_ENHANCEMENT_DEBUG: LLM service error for prospect {prospect.id}: {e}")
            emit_enhancement_progress(prospect.id, 'titles_failed', {'error': f'LLM service error: {str(e)}'})
            return False
        
        if enhanced_title['enhanced_title']:
            prospect.ai_enhanced_title = enhanced_title['enhanced_title']
            
            # Add confidence and reasoning to extras
            _ensure_extra_is_dict(prospect)
                
            prospect.extra['llm_title_enhancement'] = {
                'confidence': enhanced_title['confidence'],
                'reasoning': enhanced_title.get('reasoning', ''),
                'original_title': prospect.title,
                'model_used': llm_service.model_name,
                'enhanced_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Commit to database immediately for real-time updates
            db.session.commit()
            
            # Emit completion event with new title
            emit_enhancement_progress(prospect.id, 'titles_completed', {
                'ai_enhanced_title': enhanced_title['enhanced_title'],
                'original_title': prospect.title,
                'confidence': enhanced_title['confidence']
            })
            return True
        else:
            emit_enhancement_progress(prospect.id, 'titles_failed', {'error': 'No enhanced title generated'})
            return False
    else:
        # Not processing title - emit skipped completion
        if not prospect.title:
            reason = 'No title available to enhance'
        else:
            reason = 'Already has enhanced title'
        
        logger.info(f"TITLE_ENHANCEMENT_DEBUG: Skipping enhancement for prospect {prospect.id}, reason: {reason}")
        emit_enhancement_progress(prospect.id, 'titles_completed', {
            'skipped': True,
            'reason': reason
        })
    
    return False

def _process_set_aside_enhancement(prospect, llm_service, force_redo):
    """Process set aside standardization and enhancement for a prospect."""
    from app.services.llm_service import LLMService
    
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
    logger.info(f"Set-aside enhancement for prospect {prospect.id}: "
                f"set_aside='{prospect.set_aside}', "
                f"standardized='{prospect.set_aside_standardized}', "
                f"force_redo={force_redo}")
    logger.info(f"Extra field type: {type(prospect.extra)}, "
                f"has original_small_business_program: {'original_small_business_program' in (prospect.extra or {})}")
    
    # Always emit start event first
    emit_enhancement_progress(prospect.id, 'set_asides_started', {
        'force_redo': force_redo,
        'has_existing_set_aside': bool(prospect.set_aside),
        'has_standardized_set_aside': bool(prospect.set_aside_standardized)
    })
    
    # Check if we should process set asides using the new standardized fields
    should_process = force_redo or not prospect.set_aside_standardized
    logger.info(f"Should process: {should_process} (force_redo={force_redo}, has_standardized={bool(prospect.set_aside_standardized)})")
    
    if should_process:
        # Get comprehensive set-aside data (handles DHS small_business_program, etc.)
        comprehensive_data = llm_service._get_comprehensive_set_aside_data(prospect.set_aside, prospect)
        logger.info(f"Comprehensive data: '{comprehensive_data}'")
        
        # Process if we have data OR if force_redo is True
        if comprehensive_data or force_redo:
            # Process set aside using the LLM service
            try:
                processed_count = llm_service.enhance_prospect_set_asides([prospect], force_redo=force_redo)
                
                if processed_count > 0:
                    # Refresh the prospect to get updated standardized data
                    db.session.refresh(prospect)
                    
                    # Check if standardization was successful
                    if prospect.set_aside_standardized:
                        # Emit completion event with new standardized set aside data
                        emit_enhancement_progress(prospect.id, 'set_asides_completed', {
                            'set_aside_standardized': prospect.set_aside_standardized,
                            'set_aside_standardized_label': prospect.set_aside_standardized_label,
                            'original_set_aside': prospect.set_aside,
                            'comprehensive_data_used': comprehensive_data
                        })
                        return True
                    else:
                        emit_enhancement_progress(prospect.id, 'set_asides_failed', {'error': 'No standardized data created'})
                        return False
                else:
                    emit_enhancement_progress(prospect.id, 'set_asides_failed', {'error': 'Set aside processing failed'})
                    return False
                    
            except Exception as e:
                logger.error(f"Error processing set aside for prospect {prospect.id}: {e}")
                emit_enhancement_progress(prospect.id, 'set_asides_failed', {'error': str(e)})
                return False
        else:
            # No comprehensive data available - emit skipped completion
            reason = 'No set aside data available to process (and not forcing)'
            logger.warning(f"Skipping set-aside enhancement: {reason}")
            emit_enhancement_progress(prospect.id, 'set_asides_completed', {
                'skipped': True,
                'reason': reason
            })
    else:
        # Not processing set aside - emit skipped completion
        reason = 'Already has standardized set aside data' if not force_redo else 'Set aside processing not needed'
        logger.info(f"Skipping set-aside enhancement: {reason}")
        
        emit_enhancement_progress(prospect.id, 'set_asides_completed', {
            'skipped': True,
            'reason': reason
        })
    
    return False

def _finalize_enhancement(prospect, llm_service, processed, enhancements, force_redo):
    """Finalize the enhancement process and return appropriate response."""
    # Always update timestamp for force_redo, even if no new enhancements
    if processed or force_redo:
        prospect.ollama_processed_at = datetime.now(timezone.utc)
        prospect.ollama_model_version = llm_service.model_name
        db.session.commit()
        
        # Emit final completion event
        emit_enhancement_progress(prospect.id, 'completed', {
            'status': 'completed',
            'processed': True,
            'enhancements': enhancements,
            'ollama_processed_at': prospect.ollama_processed_at.isoformat() if prospect.ollama_processed_at else None,
            'model_version': prospect.ollama_model_version
        })
        
        return jsonify({
            "status": "success",
            "message": f"Successfully enhanced prospect with: {', '.join(enhancements)}",
            "processed": True,
            "enhancements": enhancements
        }), 200
    else:
        # Also emit completion event for cases where no processing was needed
        emit_enhancement_progress(prospect.id, 'completed', {
            'status': 'completed',
            'processed': False,
            'enhancements': [],
            'ollama_processed_at': prospect.ollama_processed_at.isoformat() if prospect.ollama_processed_at else None,
            'reason': 'Already fully enhanced or no data to enhance'
        })
        
        return jsonify({
            "status": "success",
            "message": "Prospect already fully enhanced or no data to enhance",
            "processed": False,
            "enhancements": []
        }), 200

@llm_bp.route('/enhance-single', methods=['POST'])
@admin_required
def enhance_single_prospect():
    """Enhance a single prospect with all AI enhancements using the priority queue system"""
    try:
        # Parse and validate request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
            
        prospect_id = data.get('prospect_id')
        if not prospect_id:
            return jsonify({"error": "prospect_id is required"}), 400
            
        force_redo = data.get('force_redo', False)
        user_id = data.get('user_id', 1)  # Default to 1 if no user provided
        enhancement_type = data.get('enhancement_type', 'all')
            
        # Get the prospect
        prospect = Prospect.query.get(prospect_id)
        if not prospect:
            return jsonify({"error": "Prospect not found"}), 404
        
        # Check if prospect is already being enhanced by another user
        if prospect.enhancement_status == 'in_progress':
            logger.info(f"Prospect {prospect_id} is in_progress: user_id={user_id}, enhancement_user_id={prospect.enhancement_user_id}")
            if prospect.enhancement_user_id != user_id:
                logger.warning(f"User conflict for prospect {prospect_id}: requesting user={user_id}, locked by user={prospect.enhancement_user_id}")
                return jsonify({
                    "error": "Prospect is currently being enhanced by another user",
                    "status": "blocked",
                    "enhancement_status": "in_progress",
                    "enhancement_user_id": prospect.enhancement_user_id
                }), 409
                
        # Also check if prospect is already in the queue with a different user
        # This prevents race conditions between queue processing and database locking
        existing_queue_items = [
            item for item in enhancement_queue_service._queue_items.values()
            if (str(item.prospect_id) == str(prospect_id) and 
                item.type.value == 'individual' and
                item.status.value in ['pending', 'processing'])
        ]
        
        if existing_queue_items:
            existing_item = existing_queue_items[0]
            if existing_item.user_id != user_id:
                return jsonify({
                    "error": "Prospect is currently being enhanced by another user (queued)",
                    "status": "blocked", 
                    "enhancement_status": "queued",
                    "queue_user_id": existing_item.user_id
                }), 409
            else:
                # Same user, return existing queue item
                logger.info(f"Returning existing queue item {existing_item.id} for same user {user_id}")
                return jsonify({
                    "status": "queued",
                    "message": f"Enhancement request already queued for prospect {prospect_id}",
                    "queue_item_id": existing_item.id,
                    "prospect_id": prospect_id,
                    "priority": "high",
                    "was_existing": True
                }), 200
                
        # Add to priority queue (returns dict with queue_item_id and was_existing)
        enhancement_result = enhancement_queue_service.add_individual_enhancement(
            prospect_id=prospect_id,
            enhancement_type=enhancement_type,
            user_id=user_id,
            force_redo=force_redo
        )
        
        queue_item_id = enhancement_result["queue_item_id"]
        was_existing = enhancement_result["was_existing"]
        
        # Get queue status to provide better response information
        queue_status = enhancement_queue_service.get_queue_status()
        worker_running = queue_status.get('worker_running', False)
        queue_position = None
        
        # Find the position of this item in the queue
        if queue_status.get('pending_items'):
            for idx, item in enumerate(queue_status['pending_items']):
                if item.get('id') == queue_item_id:
                    queue_position = idx + 1
                    break
        
        logger.info(f"Added individual enhancement for prospect {prospect_id} to queue with ID {queue_item_id} (worker_running={worker_running}, position={queue_position})")
        
        # Create appropriate message based on worker status
        if not worker_running:
            message = f"Enhancement queued and worker auto-started for prospect {prospect_id}"
        elif was_existing:
            message = f"Enhancement request already in progress for prospect {prospect_id}"
        else:
            message = f"Enhancement request queued for prospect {prospect_id}"
        
        return jsonify({
            "status": "queued",
            "message": message,
            "queue_item_id": queue_item_id,
            "prospect_id": prospect_id,
            "priority": "high",
            "was_existing": was_existing,
            "worker_running": worker_running,
            "queue_position": queue_position,
            "queue_size": queue_status.get('queue_size', 0)
        }), 200
            
    except Exception as e:
        logger.error(f"Error queueing single prospect enhancement: {e}", exc_info=True)
        return jsonify({"error": f"Failed to queue prospect enhancement: {str(e)}"}), 500


@llm_bp.route('/cleanup-stale-locks', methods=['POST'])
@admin_required
def cleanup_stale_enhancement_locks():
    """Clean up enhancement locks that are older than 10 minutes"""
    try:
        # Calculate cutoff time (10 minutes ago)
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        # Find prospects with stale locks
        stale_prospects = db.session.query(Prospect).filter(
            Prospect.enhancement_status == 'in_progress',
            Prospect.enhancement_started_at < cutoff_time
        ).all()
        
        cleanup_count = 0
        for prospect in stale_prospects:
            prospect.enhancement_status = 'idle'
            prospect.enhancement_started_at = None
            prospect.enhancement_user_id = None
            cleanup_count += 1
        
        db.session.commit()
        
        logger.info(f"Cleaned up {cleanup_count} stale enhancement locks")
        return jsonify({
            "message": f"Cleaned up {cleanup_count} stale enhancement locks",
            "cleanup_count": cleanup_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up stale locks: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": f"Failed to cleanup stale locks: {str(e)}"}), 500

@llm_bp.route('/queue/status', methods=['GET'])
@admin_required
def get_queue_status():
    """Get current enhancement queue status"""
    try:
        status = enhancement_queue_service.get_queue_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting queue status: {e}", exc_info=True)
        return jsonify({"error": f"Failed to get queue status: {str(e)}"}), 500

@llm_bp.route('/queue/item/<item_id>', methods=['GET'])
@admin_required
def get_queue_item_status(item_id):
    """Get status of a specific queue item"""
    try:
        item_status = enhancement_queue_service.get_item_status(item_id)
        if not item_status:
            return jsonify({"error": "Queue item not found"}), 404
        return jsonify(item_status), 200
    except Exception as e:
        logger.error(f"Error getting queue item status: {e}", exc_info=True)
        return jsonify({"error": f"Failed to get queue item status: {str(e)}"}), 500

@llm_bp.route('/queue/item/<item_id>/cancel', methods=['POST'])
@admin_required
def cancel_queue_item(item_id):
    """Cancel a specific queue item"""
    try:
        success = enhancement_queue_service.cancel_item(item_id)
        if success:
            return jsonify({"message": f"Queue item {item_id} cancelled successfully"}), 200
        else:
            return jsonify({"error": "Cannot cancel item (not found or already processing)"}), 400
    except Exception as e:
        logger.error(f"Error cancelling queue item: {e}", exc_info=True)
        return jsonify({"error": f"Failed to cancel queue item: {str(e)}"}), 500

@llm_bp.route('/queue/start-worker', methods=['POST'])
@admin_required
def start_queue_worker():
    """Start the enhancement queue worker"""
    try:
        enhancement_queue_service.start_worker()
        return jsonify({"message": "Queue worker started successfully"}), 200
    except Exception as e:
        logger.error(f"Error starting queue worker: {e}", exc_info=True)
        return jsonify({"error": f"Failed to start queue worker: {str(e)}"}), 500

@llm_bp.route('/queue/stop-worker', methods=['POST'])
@admin_required
def stop_queue_worker():
    """Stop the enhancement queue worker"""
    try:
        enhancement_queue_service.stop_worker()
        return jsonify({"message": "Queue worker stopped successfully"}), 200
    except Exception as e:
        logger.error(f"Error stopping queue worker: {e}", exc_info=True)
        return jsonify({"error": f"Failed to stop queue worker: {str(e)}"}), 500

# Global dictionary to store SSE progress events for prospects
_enhancement_progress_events = {}

def emit_enhancement_progress(prospect_id, event_type, data):
    """Emit progress event for a specific prospect enhancement"""
    if prospect_id not in _enhancement_progress_events:
        _enhancement_progress_events[prospect_id] = []
    
    event_data = {
        'event_type': event_type,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': data
    }
    
    _enhancement_progress_events[prospect_id].append(event_data)
    logger.info(f"Emitted enhancement progress for prospect {prospect_id}: {event_type}")

@llm_bp.route('/enhancement-progress/<prospect_id>')
@admin_required
def enhancement_progress_stream(prospect_id):
    """Enhanced Server-Sent Events endpoint for real-time enhancement progress"""
    def generate():
        # Set initial connection message
        yield f"data: {json.dumps({'event_type': 'connected', 'prospect_id': prospect_id})}\n\n"
        
        # Initialize events list for this prospect if it doesn't exist
        if prospect_id not in _enhancement_progress_events:
            _enhancement_progress_events[prospect_id] = []
        
        sent_event_count = 0
        max_wait_time = 600  # 10 minutes max wait (increased)
        start_time = time.time()
        last_heartbeat = time.time()
        last_queue_check = time.time()
        
        try:
            while True:
                current_time = time.time()
                
                # Check if we've exceeded max wait time
                if current_time - start_time > max_wait_time:
                    yield f"data: {json.dumps({'event_type': 'timeout', 'reason': 'max_wait_exceeded'})}\n\n"
                    break
                
                # Send heartbeat every 30 seconds
                if current_time - last_heartbeat > 30:
                    heartbeat_event = {
                        'event_type': 'keepalive',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'data': {'connection_time': current_time - start_time}
                    }
                    yield f"data: {json.dumps(heartbeat_event)}\n\n"
                    last_heartbeat = current_time
                
                # Check queue status every 2 seconds
                if current_time - last_queue_check > 2:
                    # Get queue position for this prospect
                    queue_status = enhancement_queue_service.get_queue_status()
                    if queue_status and queue_status.get('pending_items'):
                        prospect_queue_item = None
                        queue_position = None
                        
                        for idx, item in enumerate(queue_status['pending_items']):
                            if (item.get('type') == 'individual' and 
                                str(item.get('prospect_id')) == str(prospect_id)):
                                prospect_queue_item = item
                                queue_position = idx + 1
                                break
                        
                        # If found in queue, send position update
                        if prospect_queue_item and queue_position:
                            # Calculate estimated time remaining (rough estimate: 60s per item ahead)
                            estimated_time = (queue_position - 1) * 60
                            
                            position_event = {
                                'event_type': 'queue_position_update',
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'data': {
                                    'position': queue_position,
                                    'estimated_time': estimated_time,
                                    'queue_size': len(queue_status['pending_items'])
                                }
                            }
                            yield f"data: {json.dumps(position_event)}\n\n"
                        
                        # Check if processing has started
                        if (queue_status.get('current_item') and 
                            queue_status['current_item'].get('prospect_id') == int(prospect_id)):
                            processing_event = {
                                'event_type': 'processing_started',
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'data': {'queue_item_id': queue_status['current_item'].get('id')}
                            }
                            yield f"data: {json.dumps(processing_event)}\n\n"
                    
                    last_queue_check = current_time
                
                # Send any new events for this prospect
                prospect_events = _enhancement_progress_events.get(prospect_id, [])
                new_events = prospect_events[sent_event_count:]
                
                for event in new_events:
                    yield f"data: {json.dumps(event)}\n\n"
                    sent_event_count += 1
                
                # Check if we've already sent a completion event
                has_completion_event = any(
                    event.get('event_type') == 'completed' 
                    for event in prospect_events
                )
                
                if has_completion_event and sent_event_count >= len(prospect_events):
                    # All events including completion have been sent, close the connection
                    logger.info(f"SSE all events sent including completion for prospect {prospect_id}, closing connection")
                    break
                
                # Also check if prospect has been processed (fallback check)
                if not has_completion_event and current_time - last_queue_check > 2:
                    prospect = Prospect.query.get(prospect_id)
                    if prospect and prospect.ollama_processed_at:
                        # Enhancement is complete but we haven't sent the event yet
                        completion_event = {
                            'event_type': 'completed',
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'data': {
                                'status': 'completed',
                                'ollama_processed_at': prospect.ollama_processed_at.isoformat() if prospect.ollama_processed_at else None
                            }
                        }
                        logger.info(f"SSE sending completion event for prospect {prospect_id}")
                        yield f"data: {json.dumps(completion_event)}\n\n"
                        logger.info(f"SSE completion event sent for prospect {prospect_id}")
                        break
                
                # Wait before checking again (reduced for better responsiveness)
                time.sleep(0.2)
                
        except GeneratorExit:
            # Client disconnected
            logger.info(f"Client disconnected from enhancement progress stream for prospect {prospect_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for prospect {prospect_id}: {e}")
            error_event = {
                'event_type': 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': {'error': str(e)}
            }
            yield f"data: {json.dumps(error_event)}\n\n"
        finally:
            # Clean up old events for this prospect (keep only last hour)
            if prospect_id in _enhancement_progress_events:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
                _enhancement_progress_events[prospect_id] = [
                    event for event in _enhancement_progress_events[prospect_id]
                    if datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')) > cutoff_time
                ]

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )


@llm_bp.route('/enhancement-queue/<queue_item_id>', methods=['DELETE'])
@admin_required
def cancel_enhancement(queue_item_id):
    """Cancel a queued enhancement request"""
    try:
        # Attempt to cancel the queue item
        success = enhancement_queue_service.cancel_item(queue_item_id)
        
        if success:
            logger.info(f"Successfully cancelled enhancement queue item: {queue_item_id}")
            return jsonify({
                "success": True,
                "message": "Enhancement request cancelled successfully"
            }), 200
        else:
            logger.warning(f"Failed to cancel enhancement queue item: {queue_item_id} (not found or already processing)")
            return jsonify({
                "success": False,
                "error": "Queue item not found or already processing"
            }), 404
            
    except Exception as e:
        logger.error(f"Error cancelling enhancement queue item {queue_item_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Failed to cancel enhancement request"
        }), 500