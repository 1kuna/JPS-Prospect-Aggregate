from flask import Blueprint, jsonify, request
from app.database.models import Prospect, db, AIEnrichmentLog, LLMOutput
from app.utils.logger import logger
from app.services.contract_llm_service import ContractLLMService
from app.services.iterative_llm_service_v2 import iterative_service_v2 as iterative_service
from sqlalchemy import func
from datetime import datetime
import time
import asyncio

llm_bp = Blueprint('llm_api', __name__, url_prefix='/api/llm')

@llm_bp.route('/status', methods=['GET'])
def get_llm_status():
    """Get current LLM processing status and statistics"""
    try:
        # Get total prospects count
        total_prospects = db.session.query(func.count(Prospect.id)).scalar()
        
        # Get processed prospects count
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
        
        # Get contact extraction statistics
        contact_extracted_count = db.session.query(func.count(Prospect.id)).filter(
            Prospect.primary_contact_email.isnot(None)
        ).scalar()
        
        contact_extraction_percentage = (contact_extracted_count / total_prospects * 100) if total_prospects > 0 else 0
        
        # Get title enhancement statistics
        title_enhanced_count = db.session.query(func.count(Prospect.id)).filter(
            Prospect.ai_enhanced_title.isnot(None)
        ).scalar()
        
        title_enhancement_percentage = (title_enhanced_count / total_prospects * 100) if total_prospects > 0 else 0
        
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
            "contact_extraction": {
                "extracted_count": contact_extracted_count,
                "total_percentage": round(contact_extraction_percentage, 1)
            },
            "title_enhancement": {
                "enhanced_count": title_enhanced_count,
                "total_percentage": round(title_enhancement_percentage, 1)
            },
            "last_processed": last_processed,
            "model_version": model_version
        }
        
        logger.info(f"Retrieved LLM status: {processed_prospects}/{total_prospects} processed")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting LLM status: {e}", exc_info=True)
        return jsonify({"error": "Failed to get LLM status"}), 500

@llm_bp.route('/enhance', methods=['POST'])
def trigger_llm_enhancement():
    """Trigger LLM enhancement for prospects using Ollama and qwen3:8b"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
            
        enhancement_type = data.get('enhancement_type', 'all')
        limit = data.get('limit', 10)  # Changed default from 100 to 10
        
        # Validate enhancement type
        valid_types = ['values', 'contacts', 'naics', 'titles', 'all']
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
        elif enhancement_type == 'contacts':
            processed_count = llm_service.enhance_prospect_contacts(prospects)
        elif enhancement_type == 'naics':
            processed_count = llm_service.enhance_prospect_naics(prospects)
        elif enhancement_type == 'all':
            results = llm_service.enhance_all_prospects(limit=limit)
            processed_count = results['values_enhanced'] + results['contacts_enhanced'] + results['naics_enhanced']
        
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
def preview_llm_enhancement():
    """Preview LLM enhancement for a single prospect without saving"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
            
        prospect_id = data.get('prospect_id')
        enhancement_types = data.get('enhancement_types', ['values', 'contacts', 'naics'])
        
        if not prospect_id:
            return jsonify({"error": "prospect_id is required"}), 400
            
        # Get the prospect
        prospect = Prospect.query.get(prospect_id)
        if not prospect:
            return jsonify({"error": "Prospect not found"}), 404
            
        # Initialize the LLM service
        llm_service = ContractLLMService(model_name='qwen3:latest')
        
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
        
        if 'contacts' in enhancement_types and prospect.extra:
            # Extract contact data from extra field
            contact_data = {}
            if 'contacts' in prospect.extra:
                contact_data = prospect.extra['contacts']
            else:
                contact_data = {
                    'email': prospect.extra.get('contact_email') or prospect.extra.get('poc_email'),
                    'name': prospect.extra.get('contact_name') or prospect.extra.get('poc_name'),
                    'phone': prospect.extra.get('contact_phone') or prospect.extra.get('poc_phone'),
                }
            
            if any(contact_data.values()):
                extracted_contact = llm_service.extract_contact_with_llm(contact_data)
                if extracted_contact['email'] or extracted_contact['name']:
                    preview_enhancements.update({
                        'primary_contact_email': extracted_contact['email'],
                        'primary_contact_name': extracted_contact['name']
                    })
                    confidence_scores['contacts'] = extracted_contact.get('confidence', 0.8)
        
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
def start_iterative_enhancement():
    """Start iterative one-by-one LLM enhancement"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
            
        enhancement_type = data.get('enhancement_type', 'all')
        
        # Validate enhancement type
        valid_types = ['values', 'contacts', 'naics', 'titles', 'all']
        if enhancement_type not in valid_types:
            return jsonify({"error": f"Invalid enhancement type. Must be one of: {valid_types}"}), 400
        
        # Start enhancement (runs in background thread)
        result = iterative_service.start_enhancement(enhancement_type)
        
        logger.info(f"Started iterative LLM enhancement: type={enhancement_type}")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error starting iterative enhancement: {e}", exc_info=True)
        return jsonify({"error": f"Failed to start iterative enhancement: {str(e)}"}), 500

@llm_bp.route('/iterative/stop', methods=['POST'])
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

@llm_bp.route('/enhance-single', methods=['POST'])
def enhance_single_prospect():
    """Enhance a single prospect with all AI enhancements"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
            
        prospect_id = data.get('prospect_id')
        if not prospect_id:
            return jsonify({"error": "prospect_id is required"}), 400
            
        # Get the prospect
        prospect = Prospect.query.get(prospect_id)
        if not prospect:
            return jsonify({"error": "Prospect not found"}), 404
            
        logger.info(f"Starting single prospect enhancement for prospect {prospect_id}")
        
        # Initialize the LLM service
        llm_service = ContractLLMService(model_name='qwen3:latest')
        
        processed = False
        enhancements = []
        
        # Process values
        value_to_parse = None
        if prospect.estimated_value_text and not prospect.estimated_value_single:
            value_to_parse = prospect.estimated_value_text
        elif prospect.estimated_value and not prospect.estimated_value_single:
            # Convert numeric value to text for LLM processing
            value_to_parse = str(prospect.estimated_value)
        
        if value_to_parse:
            parsed_value = llm_service.parse_contract_value_with_llm(value_to_parse, prospect_id=prospect.id)
            if parsed_value['single'] is not None:
                prospect.estimated_value_single = float(parsed_value['single'])
                prospect.estimated_value_min = float(parsed_value['min']) if parsed_value['min'] else float(parsed_value['single'])
                prospect.estimated_value_max = float(parsed_value['max']) if parsed_value['max'] else float(parsed_value['single'])
                # Store the text version if it didn't exist
                if not prospect.estimated_value_text:
                    prospect.estimated_value_text = value_to_parse
                processed = True
                enhancements.append('values')
        
        # Process contacts
        if prospect.extra and not prospect.primary_contact_name:
            import json
            extra_data = prospect.extra
            if isinstance(extra_data, str):
                try:
                    extra_data = json.loads(extra_data)
                except (json.JSONDecodeError, TypeError):
                    extra_data = {}
            
            # Get contact data
            if extra_data and 'contacts' in extra_data:
                contact_data = extra_data['contacts']
            elif extra_data:
                contact_data = {
                    'email': extra_data.get('contact_email') or extra_data.get('poc_email'),
                    'name': extra_data.get('contact_name') or extra_data.get('poc_name'),
                    'phone': extra_data.get('contact_phone') or extra_data.get('poc_phone'),
                }
            else:
                contact_data = {}
            
            if any(contact_data.values()):
                extracted_contact = llm_service.extract_contact_with_llm(contact_data, prospect_id=prospect.id)
                
                if extracted_contact['email'] or extracted_contact['name']:
                    prospect.primary_contact_email = extracted_contact['email']
                    prospect.primary_contact_name = extracted_contact['name']
                    processed = True
                    enhancements.append('contacts')
        
        # Process NAICS
        if prospect.description and (not prospect.naics or prospect.naics_source != 'llm_inferred'):
            classification = llm_service.classify_naics_with_llm(prospect.title, prospect.description, prospect_id=prospect.id)
            
            if classification['code']:
                prospect.naics = classification['code']
                prospect.naics_description = classification['description']
                prospect.naics_source = 'llm_inferred'
                
                # Add confidence to extras
                if not prospect.extra:
                    prospect.extra = {}
                elif isinstance(prospect.extra, str):
                    try:
                        prospect.extra = json.loads(prospect.extra)
                    except (json.JSONDecodeError, TypeError):
                        prospect.extra = {}
                
                if not isinstance(prospect.extra, dict):
                    prospect.extra = {}
                    
                prospect.extra['llm_classification'] = {
                    'naics_confidence': classification['confidence'],
                    'model_used': llm_service.model_name,
                    'classified_at': datetime.now().isoformat()
                }
                processed = True
                enhancements.append('naics')
        
        # Process titles
        if prospect.title and not prospect.ai_enhanced_title:
            enhanced_title = llm_service.enhance_title_with_llm(
                prospect.title, 
                prospect.description or "",
                prospect.agency or "",
                prospect_id=prospect.id
            )
            
            if enhanced_title['enhanced_title']:
                prospect.ai_enhanced_title = enhanced_title['enhanced_title']
                
                # Add confidence and reasoning to extras
                if not prospect.extra:
                    prospect.extra = {}
                elif isinstance(prospect.extra, str):
                    try:
                        prospect.extra = json.loads(prospect.extra)
                    except (json.JSONDecodeError, TypeError):
                        prospect.extra = {}
                
                if not isinstance(prospect.extra, dict):
                    prospect.extra = {}
                    
                prospect.extra['llm_title_enhancement'] = {
                    'confidence': enhanced_title['confidence'],
                    'reasoning': enhanced_title.get('reasoning', ''),
                    'original_title': prospect.title,
                    'model_used': llm_service.model_name,
                    'enhanced_at': datetime.now().isoformat()
                }
                processed = True
                enhancements.append('titles')
        
        if processed:
            prospect.ollama_processed_at = datetime.now()
            prospect.ollama_model_version = llm_service.model_name
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "message": f"Successfully enhanced prospect with: {', '.join(enhancements)}",
                "processed": True,
                "enhancements": enhancements
            }), 200
        else:
            return jsonify({
                "status": "success",
                "message": "Prospect already fully enhanced or no data to enhance",
                "processed": False,
                "enhancements": []
            }), 200
            
    except Exception as e:
        logger.error(f"Error enhancing single prospect: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": f"Failed to enhance prospect: {str(e)}"}), 500