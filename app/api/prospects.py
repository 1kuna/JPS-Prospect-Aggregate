from flask import Blueprint, jsonify, request
from sqlalchemy import desc, asc, or_, cast, String # Added for sorting and JSON queries
from sqlalchemy.sql import func
from app.database.crud import paginate_sqlalchemy_query
from app.models import Prospect, db # Added db for session access in new route
from app.exceptions import ValidationError, NotFoundError # Added NotFoundError
from app.utils.logger import logger

prospects_bp = Blueprint('prospects_api', __name__, url_prefix='/api/prospects')

@prospects_bp.route('', methods=['GET'])
@prospects_bp.route('/', methods=['GET'])
def get_prospects_route():
    logger.info("Received request for /api/prospects/")
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        if page <= 0:
            logger.error(f"Invalid page number: {page}. Must be > 0.")
            return jsonify({"error": "Page number must be positive"}), 400
        
        sort_by = request.args.get('sort_by', 'id', type=str)
        sort_order = request.args.get('sort_order', 'desc', type=str)
        search_term = request.args.get('search', '', type=str)
        
        # New filtering parameters
        naics_filter = request.args.get('naics', '', type=str)
        keywords_filter = request.args.get('keywords', '', type=str)
        agency_filter = request.args.get('agency', '', type=str)
        ai_enrichment_filter = request.args.get('ai_enrichment', 'all', type=str)
        
        logger.debug(f"Requesting prospects with page={page}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}, search='{search_term}', naics='{naics_filter}', keywords='{keywords_filter}', agency='{agency_filter}', ai_enrichment='{ai_enrichment_filter}'")
        
        # Construct the base query
        base_query = Prospect.query
        
        # Apply search filter if provided
        if search_term:
            search_filter = (
                (Prospect.title.ilike(f'%{search_term}%')) |
                (Prospect.description.ilike(f'%{search_term}%')) |
                (Prospect.agency.ilike(f'%{search_term}%'))
            )
            base_query = base_query.filter(search_filter)
            
        # Apply NAICS filter - check both primary and all alternate codes
        if naics_filter:
            # Check primary NAICS code OR any alternate codes in extra JSON
            # Use cast to convert JSON to string for searching
            naics_condition = or_(
                Prospect.naics.ilike(f'%{naics_filter}%'),
                cast(Prospect.extra, String).ilike(f'%{naics_filter}%')  # Search entire extra JSON
            )
            base_query = base_query.filter(naics_condition)
            
        # Apply keywords filter (search in title and description)
        if keywords_filter:
            keywords_search_filter = (
                (Prospect.title.ilike(f'%{keywords_filter}%')) |
                (Prospect.description.ilike(f'%{keywords_filter}%'))
            )
            base_query = base_query.filter(keywords_search_filter)
            
        # Apply agency filter
        if agency_filter:
            base_query = base_query.filter(Prospect.agency.ilike(f'%{agency_filter}%'))
            
        # Apply AI enrichment filter
        if ai_enrichment_filter == 'enhanced':
            # Show only prospects that have been processed by AI (have LLM timestamp)
            base_query = base_query.filter(Prospect.ollama_processed_at.isnot(None))
        elif ai_enrichment_filter == 'original':
            # Show only prospects that have NOT been processed by AI
            base_query = base_query.filter(Prospect.ollama_processed_at.is_(None))
        # 'all' or any other value means no filter applied
        
        # Apply sorting
        sort_column = getattr(Prospect, sort_by, Prospect.id) # Default to Prospect.id if sort_by is invalid
        if sort_order.lower() == 'desc':
            base_query = base_query.order_by(desc(sort_column))
        else:
            base_query = base_query.order_by(asc(sort_column))
            
        # Call the pagination function
        results = paginate_sqlalchemy_query(query=base_query, page=page, per_page=limit)

        # Convert prospect items to dictionaries
        prospect_items_dict = [prospect.to_dict() for prospect in results["items"]]
        
        # New JSON response structure
        response_data = {
            "prospects": prospect_items_dict, # Renamed from "data"
            "pagination": {                 # Full pagination details nested
                "page": results["page"],
                "per_page": results["per_page"],
                "total_items": results["total_items"],
                "total_pages": results["total_pages"],
                "has_next": results["has_next"],
                "has_prev": results["has_prev"]
            }
        }
        
        logger.info(f"Successfully retrieved {len(prospect_items_dict)} prospects for page {page}, limit {limit}.")
        return jsonify(response_data), 200

    except ValidationError as ve:
        logger.error(f"Validation error in pagination parameters: {ve}", exc_info=True)
        return jsonify({"error": str(ve)}), 400
    except ValueError as ve_param: # For Flask's type conversion errors in request.args.get
        logger.error(f"ValueError in request arguments: {ve_param}", exc_info=True)
        return jsonify({"error": "Invalid parameter type. 'page' and 'limit' must be integers."}), 400
    except Exception as e:
        logger.error(f"An unexpected error occurred in /api/prospects/: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

@prospects_bp.route('/<string:prospect_id>', methods=['GET'])
def get_prospect_by_id_route(prospect_id: str):
    logger.info(f"Received request for /api/prospects/{prospect_id}")
    try:
        # session = db.session # Not strictly necessary if using .get() on the Model itself with Flask-SQLAlchemy
        prospect = Prospect.query.get(prospect_id) # Use .get() for primary key lookup
        
        if not prospect:
            logger.warning(f"Prospect with ID {prospect_id} not found.")
            raise NotFoundError(f"Prospect with ID {prospect_id} not found.")
            
        logger.info(f"Successfully retrieved prospect with ID {prospect_id}.")
        return jsonify(prospect.to_dict()), 200
        
    except NotFoundError as nfe: # Catch specific NotFoundError
        logger.error(f"NotFoundError in get_prospect_by_id_route: {nfe}", exc_info=True)
        return jsonify({"error": str(nfe)}), 404
    except Exception as e:
        logger.error(f"An unexpected error occurred in /api/prospects/<id>: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500
