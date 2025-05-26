from flask import Blueprint, jsonify, request
from app.database.crud import get_prospects_paginated
from app.utils.logger import logger

prospects_bp = Blueprint('prospects_api', __name__, url_prefix='/api/prospects')

@prospects_bp.route('/', methods=['GET'])
def get_prospects_route():
    logger.info("Received request for /api/prospects/")
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        if page <= 0:
            logger.error(f"Invalid page number: {page}. Must be > 0.")
            return jsonify({"error": "Page number must be positive"}), 400
        if limit <= 0:
            logger.error(f"Invalid limit value: {limit}. Must be > 0.")
            return jsonify({"error": "Limit must be positive"}), 400
        
        logger.debug(f"Requesting prospects with page={page}, limit={limit}")
        results = get_prospects_paginated(page=page, per_page=limit)

        if results is None:
            # This case might occur if get_prospects_paginated itself returns None due to internal validation
            # or a database error that it handles by returning None.
            logger.error(f"Failed to retrieve prospects for page={page}, limit={limit}. get_prospects_paginated returned None.")
            return jsonify({"error": "Failed to retrieve prospects. Check server logs."}), 500

        prospect_items_dict = [prospect.to_dict() for prospect in results["items"]]
        
        response_data = {
            "data": prospect_items_dict,
            "total": results["total"],
            "totalPages": results["total_pages"],
            "currentPage": results["page"],
            "perPage": results["per_page"]
        }
        
        logger.info(f"Successfully retrieved {len(prospect_items_dict)} prospects for page {page}.")
        return jsonify(response_data), 200

    except ValueError as ve:
        logger.error(f"ValueError in request arguments: {ve}", exc_info=True)
        return jsonify({"error": "Invalid parameter type. 'page' and 'limit' must be integers."}), 400
    except Exception as e:
        logger.error(f"An unexpected error occurred in /api/prospects/: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500
