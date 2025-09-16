from flask import request
from sqlalchemy import func

from app.api.factory import (
    api_route,
    create_blueprint,
    error_response,
    success_response,
)
from app.database import db
from app.database.models import DataSource, Prospect, ScraperStatus
from app.exceptions import DatabaseError, NotFoundError, ValidationError

data_sources_bp, logger = create_blueprint("data_sources")


@api_route(data_sources_bp, "/", methods=["GET"], auth="super_admin")
def get_data_sources():
    """Get all data sources."""
    logger.info("GET /api/data-sources/ called")
    logger.info(f"User: {request.headers.get('User-Agent', 'Unknown')}")
    logger.info(f"Origin: {request.headers.get('Origin', 'No origin')}")

    session = db.session
    try:
        # Subquery for prospect counts
        prospect_count_subq = (
            session.query(
                Prospect.source_id, func.count(Prospect.id).label("prospect_count")
            )
            .group_by(Prospect.source_id)
            .subquery()
        )

        # Subquery for the latest status for each source
        # This gets the source_id and the max last_checked timestamp for that source_id
        latest_status_subq = (
            session.query(
                ScraperStatus.source_id,
                func.max(ScraperStatus.last_checked).label("max_last_checked"),
            )
            .group_by(ScraperStatus.source_id)
            .subquery()
        )

        # Main query
        query = (
            session.query(
                DataSource, prospect_count_subq.c.prospect_count, ScraperStatus
            )
            .outerjoin(
                prospect_count_subq,
                DataSource.id == prospect_count_subq.c.source_id,
            )
            .outerjoin(
                latest_status_subq,
                DataSource.id == latest_status_subq.c.source_id,
            )
            .outerjoin(
                ScraperStatus,
                (ScraperStatus.source_id == DataSource.id)
                & (ScraperStatus.last_checked == latest_status_subq.c.max_last_checked),
            )
        )

        results = query.all()

        data_sources = []
        for data_source, prospect_count, status in results:
            data_source_dict = data_source.to_dict()
            data_source_dict["prospect_count"] = prospect_count or 0

            # Add status information if available
            if status:
                data_source_dict["last_status"] = {
                    "status": status.status,
                    "last_checked": (
                        status.last_checked.isoformat() + "Z"
                        if status.last_checked
                        else None
                    ),
                    "records_found": status.records_found,
                    "error_message": status.error_message,
                    "details": status.details,
                }
            else:
                data_source_dict["last_status"] = None

            data_sources.append(data_source_dict)

        logger.info(f"Returning {len(data_sources)} data sources")
        return success_response(data=data_sources)

    except DatabaseError as de:
        raise de  # Re-raise to be handled by api_route
    except Exception as e:
        logger.error(f"Error fetching data sources: {str(e)}", exc_info=True)
        return error_response(500, "An unexpected error occurred")


@api_route(data_sources_bp, "/<int:source_id>", methods=["GET"], auth="super_admin")
def get_data_source(source_id):
    """Get a specific data source by ID."""
    session = db.session
    try:
        # Similar complex query as above but for a single source
        prospect_count_subq = (
            session.query(
                Prospect.source_id, func.count(Prospect.id).label("prospect_count")
            )
            .filter(Prospect.source_id == source_id)
            .group_by(Prospect.source_id)
            .subquery()
        )

        latest_status_subq = (
            session.query(
                ScraperStatus.source_id,
                func.max(ScraperStatus.last_checked).label("max_last_checked"),
            )
            .filter(ScraperStatus.source_id == source_id)
            .group_by(ScraperStatus.source_id)
            .subquery()
        )

        query = (
            session.query(
                DataSource, prospect_count_subq.c.prospect_count, ScraperStatus
            )
            .filter(DataSource.id == source_id)
            .outerjoin(
                prospect_count_subq,
                DataSource.id == prospect_count_subq.c.source_id,
            )
            .outerjoin(
                latest_status_subq,
                DataSource.id == latest_status_subq.c.source_id,
            )
            .outerjoin(
                ScraperStatus,
                (ScraperStatus.source_id == DataSource.id)
                & (ScraperStatus.last_checked == latest_status_subq.c.max_last_checked),
            )
        )

        result = query.first()

        if not result:
            raise NotFoundError(f"Data source with ID {source_id} not found")

        data_source, prospect_count, status = result
        data_source_dict = data_source.to_dict()
        data_source_dict["prospect_count"] = prospect_count or 0

        if status:
            data_source_dict["last_status"] = {
                "status": status.status,
                "last_checked": (
                    status.last_checked.isoformat() + "Z"
                    if status.last_checked
                    else None
                ),
                "records_found": status.records_found,
                "error_message": status.error_message,
                "details": status.details,
            }
        else:
            data_source_dict["last_status"] = None

        return success_response(data={"data_source": data_source_dict})

    except NotFoundError as nfe:
        raise nfe  # Re-raise to be handled by api_route
    except DatabaseError as de:
        raise de  # Re-raise
    except Exception as e:
        logger.error(f"Error fetching data source {source_id}: {str(e)}", exc_info=True)
        return error_response(500, "An unexpected error occurred")


@api_route(data_sources_bp, "/", methods=["POST"], auth="super_admin")
def create_data_source():
    """Create a new data source."""
    try:
        data = request.get_json()
        if not data:
            return error_response(400, "Request body is required")

        # Validate required fields
        if not data.get("name"):
            return error_response(400, "Data source name is required")

        # Check for duplicate name
        existing = db.session.query(DataSource).filter_by(name=data.get("name")).first()
        if existing:
            return error_response(
                409, f"Data source with name '{data.get('name')}' already exists"
            )

        # Create new data source
        data_source = DataSource(
            name=data.get("name"),
            description=data.get("description", ""),
        )

        db.session.add(data_source)
        db.session.commit()

        logger.info(
            f"Created new data source: {data_source.name} (ID: {data_source.id})"
        )

        return success_response(
            data={"data_source": data_source.to_dict()},
            message="Data source created successfully",
            status_code=201,
        )

    except ValidationError as ve:
        raise ve  # Re-raise to be handled by api_route
    except Exception as e:
        logger.error(f"Error creating data source: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to create data source")


@api_route(data_sources_bp, "/<int:source_id>", methods=["PUT"], auth="super_admin")
def update_data_source(source_id):
    """Update a data source."""
    try:
        data = request.get_json()
        if not data:
            return error_response(400, "Request body is required")

        data_source = db.session.query(DataSource).filter_by(id=source_id).first()
        if not data_source:
            raise NotFoundError(f"Data source with ID {source_id} not found")

        # Update fields if provided
        if "name" in data:
            # Check for duplicate name
            existing = (
                db.session.query(DataSource)
                .filter(DataSource.name == data["name"], DataSource.id != source_id)
                .first()
            )
            if existing:
                return error_response(
                    409, f"Data source with name '{data['name']}' already exists"
                )
            data_source.name = data["name"]

        if "description" in data:
            data_source.description = data["description"]

        db.session.commit()

        logger.info(f"Updated data source: {data_source.name} (ID: {data_source.id})")

        return success_response(
            data={"data_source": data_source.to_dict()},
            message="Data source updated successfully",
        )

    except NotFoundError as nfe:
        raise nfe  # Re-raise to be handled by api_route
    except ValidationError as ve:
        raise ve  # Re-raise
    except Exception as e:
        logger.error(f"Error updating data source {source_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to update data source")


@api_route(data_sources_bp, "/<int:source_id>", methods=["DELETE"], auth="super_admin")
def delete_data_source(source_id):
    """Delete a data source and all related data."""
    try:
        data_source = db.session.query(DataSource).filter_by(id=source_id).first()
        if not data_source:
            raise NotFoundError(f"Data source with ID {source_id} not found")

        # Count related prospects
        prospect_count = (
            db.session.query(func.count(Prospect.id))
            .filter(Prospect.source_id == source_id)
            .scalar()
        )

        # Delete related prospects first (cascade might not be configured)
        db.session.query(Prospect).filter(Prospect.source_id == source_id).delete()

        # Delete related scraper status
        db.session.query(ScraperStatus).filter(
            ScraperStatus.source_id == source_id
        ).delete()

        # Delete the data source
        db.session.delete(data_source)
        db.session.commit()

        logger.info(
            f"Deleted data source: {data_source.name} (ID: {source_id}) and {prospect_count} related prospects"
        )

        return success_response(
            message=f"Data source '{data_source.name}' and {prospect_count} related prospects deleted successfully"
        )

    except NotFoundError as nfe:
        raise nfe  # Re-raise to be handled by api_route
    except Exception as e:
        logger.error(f"Error deleting data source {source_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to delete data source")


@api_route(
    data_sources_bp, "/<int:source_id>/clear-data", methods=["POST"], auth="super_admin"
)
def clear_data_source_data(source_id):
    """Clear all prospect data for a specific data source without deleting the source.

    Returns the number of deleted prospect records.
    """
    try:
        data_source = db.session.query(DataSource).filter_by(id=source_id).first()
        if not data_source:
            raise NotFoundError(f"Data source with ID {source_id} not found")

        # Count related prospects
        prospect_count = (
            db.session.query(func.count(Prospect.id))
            .filter(Prospect.source_id == source_id)
            .scalar()
        )

        # Delete related prospects
        db.session.query(Prospect).filter(Prospect.source_id == source_id).delete()
        db.session.commit()

        logger.info(
            f"Cleared {prospect_count} prospects for data source: {data_source.name} (ID: {source_id})"
        )

        return success_response(
            message=f"Cleared {prospect_count} prospects for '{data_source.name}'",
            data={"deleted_count": prospect_count},
        )
    except NotFoundError as nfe:
        raise nfe
    except Exception as e:
        logger.error(
            f"Error clearing data for data source {source_id}: {str(e)}",
            exc_info=True,
        )
        db.session.rollback()
        return error_response(500, "Failed to clear data source data")
