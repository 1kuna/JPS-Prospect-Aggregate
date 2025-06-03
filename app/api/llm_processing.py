from flask import Blueprint, jsonify, request
from app.database.models import Prospect, db
from app.utils.logger import logger
from sqlalchemy import func
from datetime import datetime
import subprocess
import json

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
    """Trigger LLM enhancement for prospects"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
            
        enhancement_type = data.get('enhancement_type', 'all')
        limit = data.get('limit', 100)
        
        # Validate enhancement type
        valid_types = ['values', 'contacts', 'naics', 'all']
        if enhancement_type not in valid_types:
            return jsonify({"error": f"Invalid enhancement type. Must be one of: {valid_types}"}), 400
            
        # For now, return a mock successful response
        # In a real implementation, this would trigger the actual LLM processing
        logger.info(f"Mock LLM enhancement triggered: type={enhancement_type}, limit={limit}")
        
        response_data = {
            "message": f"LLM enhancement started for {enhancement_type}",
            "processed_count": min(limit, 50),  # Mock processed count
            "duration": 45.2,  # Mock duration
            "enhancement_type": enhancement_type
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error triggering LLM enhancement: {e}", exc_info=True)
        return jsonify({"error": "Failed to trigger LLM enhancement"}), 500

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
            
        # For now, return mock preview data
        mock_preview = {
            "prospect_id": prospect_id,
            "original_data": {
                "title": prospect.title,
                "estimated_value_text": prospect.estimated_value_text,
                "naics": prospect.naics,
                "naics_source": prospect.naics_source
            },
            "preview_enhancements": {
                "estimated_value_single": 250000.0 if 'values' in enhancement_types else None,
                "estimated_value_min": 200000.0 if 'values' in enhancement_types else None,
                "estimated_value_max": 300000.0 if 'values' in enhancement_types else None,
                "primary_contact_email": "contact@example.gov" if 'contacts' in enhancement_types else None,
                "primary_contact_name": "John Smith" if 'contacts' in enhancement_types else None,
                "naics": "541511" if 'naics' in enhancement_types and not prospect.naics else prospect.naics,
                "naics_source": "llm_inferred" if 'naics' in enhancement_types and not prospect.naics else prospect.naics_source
            },
            "confidence_scores": {
                "values": 0.85 if 'values' in enhancement_types else None,
                "contacts": 0.72 if 'contacts' in enhancement_types else None,
                "naics": 0.91 if 'naics' in enhancement_types else None
            }
        }
        
        logger.info(f"Generated LLM preview for prospect {prospect_id}")
        return jsonify(mock_preview), 200
        
    except Exception as e:
        logger.error(f"Error generating LLM preview: {e}", exc_info=True)
        return jsonify({"error": "Failed to generate LLM preview"}), 500