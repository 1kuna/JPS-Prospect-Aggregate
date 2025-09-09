from flask import request
from sqlalchemy import (
    String,
    asc,
    cast,
    desc,
    or_,
)

from app.api.factory import (
    api_route,
    create_blueprint,
    error_response,
    paginated_response,
)
from app.database.crud import paginate_sqlalchemy_query
from app.database.models import Prospect
from app.exceptions import ValidationError

prospects_bp, logger = create_blueprint("prospects_api", "/api/prospects")


@api_route(prospects_bp, "", methods=["GET"])
def get_prospects_route():
    # Only log errors and warnings, not successful requests to reduce noise
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 10, type=int)

        if page <= 0:
            logger.error(f"Invalid page number: {page}. Must be > 0.")
            return error_response(400, "Page number must be positive")

        sort_by = request.args.get("sort_by", "id", type=str)
        sort_order = request.args.get("sort_order", "desc", type=str)
        search_term = request.args.get("search", "", type=str)

        # New filtering parameters
        naics_filter = request.args.get("naics", "", type=str)
        keywords_filter = request.args.get("keywords", "", type=str)
        ai_enrichment_filter = request.args.get("ai_enrichment", "all", type=str)
        source_ids_filter = request.args.get(
            "source_ids", "", type=str
        )  # Comma-separated list of source IDs

        # Debug logging only when filters are applied to avoid noise
        if (
            search_term
            or naics_filter
            or keywords_filter
            or ai_enrichment_filter != "all"
            or source_ids_filter
        ):
            logger.debug(
                f"Requesting prospects with filters: search='{search_term}', naics='{naics_filter}', keywords='{keywords_filter}', ai_enrichment='{ai_enrichment_filter}', source_ids='{source_ids_filter}'"
            )

        # Construct the base query
        base_query = Prospect.query

        # Apply search filter if provided
        if search_term:
            search_filter = (
                (Prospect.title.ilike(f"%{search_term}%"))
                | (Prospect.description.ilike(f"%{search_term}%"))
                | (Prospect.agency.ilike(f"%{search_term}%"))
            )
            base_query = base_query.filter(search_filter)

        # Apply NAICS filter - check both primary and all alternate codes
        if naics_filter:
            # Check primary NAICS code OR any alternate codes in extra JSON
            # Use cast to convert JSON to string for searching
            naics_condition = or_(
                Prospect.naics.ilike(f"%{naics_filter}%"),
                cast(Prospect.extra, String).ilike(
                    f"%{naics_filter}%"
                ),  # Search entire extra JSON
            )
            base_query = base_query.filter(naics_condition)

        # Apply keywords filter (search in title and description)
        if keywords_filter:
            keywords_search_filter = (Prospect.title.ilike(f"%{keywords_filter}%")) | (
                Prospect.description.ilike(f"%{keywords_filter}%")
            )
            base_query = base_query.filter(keywords_search_filter)

        # Apply AI enrichment filter
        if ai_enrichment_filter == "enhanced":
            # Show only prospects that have been processed by AI (have LLM timestamp)
            base_query = base_query.filter(Prospect.ollama_processed_at.isnot(None))
        elif ai_enrichment_filter == "original":
            # Show only prospects that have NOT been processed by AI
            base_query = base_query.filter(Prospect.ollama_processed_at.is_(None))
        # 'all' or any other value means no filter applied

        # Apply source IDs filter
        if source_ids_filter:
            try:
                # Parse comma-separated source IDs and convert to integers
                source_ids = [
                    int(id.strip()) for id in source_ids_filter.split(",") if id.strip()
                ]
                if source_ids:
                    base_query = base_query.filter(Prospect.source_id.in_(source_ids))
            except ValueError:
                # Log warning for invalid source ID format but continue without filter
                logger.warning(
                    f"Invalid source_ids format: '{source_ids_filter}'. Expected comma-separated integers."
                )

        # Apply sorting
        sort_column = getattr(
            Prospect, sort_by, Prospect.id
        )  # Default to Prospect.id if sort_by is invalid
        if sort_order.lower() == "desc":
            base_query = base_query.order_by(desc(sort_column))
        else:
            base_query = base_query.order_by(asc(sort_column))

        # Call the pagination function
        results = paginate_sqlalchemy_query(query=base_query, page=page, per_page=limit)

        # Convert prospect items to dictionaries
        prospect_items_dict = [prospect.to_dict() for prospect in results["items"]]

        # Use paginated_response helper
        return paginated_response(
            items=prospect_items_dict,
            page=results["page"],
            per_page=results["per_page"],
            total_items=results["total_items"],
            total_pages=results["total_pages"],
            prospects=prospect_items_dict  # Keep "prospects" key for backward compat
        )

    except ValidationError as ve:
        raise ve  # Let api_route decorator handle it
    except ValueError as ve_param:
        logger.error(f"ValueError in request arguments: {ve_param}", exc_info=True)
        return error_response(400, "Invalid parameter type. 'page' and 'limit' must be integers.")
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in /api/prospects/: {e}", exc_info=True
        )
        return jsonify(
            {"error": "An unexpected error occurred. Please try again later."}
        ), 500


@prospects_bp.route("/<string:prospect_id>", methods=["GET"])
def get_prospect_by_id_route(prospect_id: str):
    # Only log errors and warnings for individual prospect requests
    try:
        # session = db.session # Not strictly necessary if using .get() on the Model itself with Flask-SQLAlchemy
        prospect = Prospect.query.get(prospect_id)  # Use .get() for primary key lookup

        if not prospect:
            logger.warning(f"Prospect with ID {prospect_id} not found.")
            raise NotFoundError(f"Prospect with ID {prospect_id} not found.")

        logger.info(f"Successfully retrieved prospect with ID {prospect_id}.")
        return jsonify(prospect.to_dict()), 200

    except NotFoundError as nfe:  # Catch specific NotFoundError
        logger.error(f"NotFoundError in get_prospect_by_id_route: {nfe}", exc_info=True)
        return jsonify({"error": str(nfe)}), 404
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in /api/prospects/<id>: {e}", exc_info=True
        )
        return jsonify(
            {"error": "An unexpected error occurred. Please try again later."}
        ), 500
