"""
API endpoints for controlling LLM processing of prospects
"""

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
import logging

from app.database import db
from app.database.crud import get_prospects_for_llm_enhancement, get_prospect_statistics
from app.services.contract_llm_service import ContractLLMService
from app.api.errors import error_response, bad_request

logger = logging.getLogger(__name__)

bp = Blueprint('llm_processing', __name__, url_prefix='/api/llm')


@bp.route('/status', methods=['GET'])
@cross_origin()
def get_llm_status():
    """
    Get the status of LLM processing including statistics.
    
    Returns:
        JSON response with processing statistics
    """
    try:
        stats = get_prospect_statistics()
        
        # Check if Ollama is available
        ollama_available = False
        try:
            from app.utils.llm_utils import call_ollama
            test_response = call_ollama("test", "qwen3:8b")
            ollama_available = test_response is not None
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'ollama_available': ollama_available,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting LLM status: {e}")
        return error_response(500, "Failed to get LLM processing status")


@bp.route('/enhance', methods=['POST'])
@cross_origin()
def enhance_prospects():
    """
    Start LLM enhancement for prospects.
    
    Request body:
    {
        "enhancement_type": "values|contacts|naics|all",
        "limit": 100  # optional, max number to process
    }
    
    Returns:
        JSON response with enhancement results
    """
    data = request.get_json()
    
    if not data:
        return bad_request("No data provided")
    
    enhancement_type = data.get('enhancement_type', 'all')
    limit = data.get('limit', 100)
    
    if enhancement_type not in ['values', 'contacts', 'naics', 'all']:
        return bad_request(f"Invalid enhancement type: {enhancement_type}")
    
    if not isinstance(limit, int) or limit < 1:
        return bad_request("Limit must be a positive integer")
    
    try:
        # Initialize LLM service
        llm_service = ContractLLMService()
        
        # Get prospects to enhance
        prospects = get_prospects_for_llm_enhancement(enhancement_type, limit)
        
        if not prospects:
            return jsonify({
                'success': True,
                'message': 'No prospects found needing enhancement',
                'enhanced_count': 0
            })
        
        # Run enhancement based on type
        if enhancement_type == 'values':
            enhanced_count = llm_service.enhance_prospect_values(prospects)
        elif enhancement_type == 'contacts':
            enhanced_count = llm_service.enhance_prospect_contacts(prospects)
        elif enhancement_type == 'naics':
            enhanced_count = llm_service.enhance_prospect_naics(prospects)
        else:  # 'all'
            results = llm_service.enhance_all_prospects(limit=limit)
            enhanced_count = sum(v for k, v in results.items() if k != 'total_prospects')
        
        return jsonify({
            'success': True,
            'enhancement_type': enhancement_type,
            'prospects_processed': len(prospects),
            'enhanced_count': enhanced_count,
            'message': f'Successfully enhanced {enhanced_count} prospects'
        })
        
    except Exception as e:
        logger.error(f"Error enhancing prospects: {e}")
        return error_response(500, f"Failed to enhance prospects: {str(e)}")


@bp.route('/preview', methods=['POST'])
@cross_origin()
def preview_enhancement():
    """
    Preview LLM enhancement for a single prospect without saving.
    
    Request body:
    {
        "prospect_id": "abc123",
        "enhancement_types": ["values", "contacts", "naics"]  # optional, defaults to all
    }
    
    Returns:
        JSON response with preview of enhancements
    """
    data = request.get_json()
    
    if not data or 'prospect_id' not in data:
        return bad_request("prospect_id is required")
    
    prospect_id = data['prospect_id']
    enhancement_types = data.get('enhancement_types', ['values', 'contacts', 'naics'])
    
    try:
        from app.database.models import Prospect
        
        prospect = Prospect.query.filter_by(id=prospect_id).first()
        if not prospect:
            return bad_request(f"Prospect not found: {prospect_id}")
        
        llm_service = ContractLLMService()
        preview_results = {}
        
        # Preview value parsing
        if 'values' in enhancement_types and prospect.estimated_value_text:
            parsed_values = llm_service.parse_contract_value_with_llm(prospect.estimated_value_text)
            preview_results['parsed_values'] = {
                'original_text': prospect.estimated_value_text,
                'parsed': parsed_values
            }
        
        # Preview contact extraction
        if 'contacts' in enhancement_types and prospect.extra:
            contact_data = prospect.extra.get('contacts', {})
            if contact_data:
                extracted_contact = llm_service.extract_contact_with_llm(contact_data)
                preview_results['extracted_contact'] = {
                    'source_data': contact_data,
                    'extracted': extracted_contact
                }
        
        # Preview NAICS classification
        if 'naics' in enhancement_types and not prospect.naics:
            if prospect.title and prospect.description:
                classification = llm_service.classify_naics_with_llm(
                    prospect.title, 
                    prospect.description
                )
                preview_results['naics_classification'] = classification
        
        return jsonify({
            'success': True,
            'prospect_id': prospect_id,
            'current_data': {
                'title': prospect.title,
                'naics': prospect.naics,
                'naics_source': prospect.naics_source,
                'estimated_value_text': prospect.estimated_value_text,
                'primary_contact_email': prospect.primary_contact_email
            },
            'preview_enhancements': preview_results
        })
        
    except Exception as e:
        logger.error(f"Error previewing enhancement: {e}")
        return error_response(500, f"Failed to preview enhancement: {str(e)}")


@bp.route('/batch-status/<int:batch_id>', methods=['GET'])
@cross_origin()
def get_batch_status(batch_id):
    """
    Get the status of a batch enhancement job.
    
    Note: This is a placeholder for future async processing implementation.
    """
    return jsonify({
        'success': False,
        'message': 'Batch processing not yet implemented'
    })


# Register blueprint
def register_llm_api(app):
    """Register LLM processing API blueprint with the Flask app"""
    app.register_blueprint(bp)