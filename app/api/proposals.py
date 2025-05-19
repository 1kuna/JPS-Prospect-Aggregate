from flask import Blueprint, request, jsonify
from sqlalchemy import desc, asc
from app.models import db, Prospect
from app.exceptions import ValidationError, NotFoundError
from app.utils.logger import logger
import math

proposals_bp = Blueprint('proposals', __name__)

# Set up logging using the centralized utility
logger = logger.bind(name="api.proposals")

def paginate_query(query, page, per_page):
    """Helper function to paginate query results."""
    # Validate pagination parameters
    try:
        page = int(page)
        if page < 1:
            raise ValidationError("Page number must be greater than or equal to 1")
    except ValueError:
        raise ValidationError("Page number must be an integer")
    
    try:
        per_page = int(per_page)
        if per_page < 1:
            raise ValidationError("Per page must be greater than or equal to 1")
        if per_page > 100: # Max per_page can be adjusted
            raise ValidationError("Per page cannot exceed 100")
    except ValueError:
        raise ValidationError("Per page must be an integer")
    
    # Calculate pagination offsets
    offset = (page - 1) * per_page
    
    # Calculate total items and pages
    total_items = query.count()
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    
    # Apply pagination to query
    paginated_query = query.offset(offset).limit(per_page)
    
    # Create pagination info
    pagination = {
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }
    
    return paginated_query, pagination


@proposals_bp.route('/', methods=['GET'])
def get_proposals():
    """Get all proposals with pagination and filtering."""
    try:
        # Get query parameters
        page = request.args.get('page', 1)
        per_page = request.args.get('per_page', 10)
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'desc')
        search_term = request.args.get('search', '')
        
        session = db.session
        # Build base query
        query = session.query(Prospect)
        
        # Apply search filter if provided
        if search_term:
            search_filter = (
                (Prospect.title.ilike(f'%{search_term}%')) |
                (Prospect.description.ilike(f'%{search_term}%')) |
                (Prospect.agency.ilike(f'%{search_term}%'))
            )
            query = query.filter(search_filter)
        
        # Apply sorting
        sort_column = getattr(Prospect, sort_by, Prospect.id)
        if sort_order == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination using the helper
        paginated_query, pagination_info = paginate_query(query, page, per_page)
        prospects_data = paginated_query.all()

        # Convert to dictionary
        prospects_dict = [p.to_dict() for p in prospects_data]
        
        return jsonify({
            'proposals': prospects_dict,
            'pagination': pagination_info
        })
            
    except ValidationError as ve:
        raise ve # Re-raise validation errors from paginate_query
    except Exception as e: # General SQLAlchemyError or other unexpected errors
        logger.error(f"Database or unexpected error in get_proposals: {str(e)}", exc_info=True)
        db.session.rollback() # Rollback in case of error
        raise # Re-raise to be handled by global error handlers


@proposals_bp.route('/<string:prospect_id>', methods=['GET'])
def get_proposal(prospect_id):
    """Get a specific prospect by ID."""
    session = db.session
    prospect = session.query(Prospect).get(prospect_id)
    if not prospect:
        raise NotFoundError(f"Prospect with ID {prospect_id} not found")
    return jsonify(prospect.to_dict())

# ... existing code ...
# Add proposal-related routes here 