from flask import Blueprint, request, jsonify
from sqlalchemy import func
from app.models import db, Prospect, DataSource, ScraperStatus
from app.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.logger import logger
# import datetime # Unused

data_sources_bp = Blueprint('data_sources', __name__)

# Set up logging using the centralized utility
logger = logger.bind(name="api.data_sources")

@data_sources_bp.route('/', methods=['GET'])
def get_data_sources():
    """Get all data sources."""
    session = db.session
    try:
        # Subquery for prospect counts
        prospect_count_subq = session.query(
            Prospect.source_id,
            func.count(Prospect.id).label("prospect_count")
        ).group_by(Prospect.source_id).subquery()

        # Subquery for the latest status for each source
        # This gets the source_id and the max last_checked timestamp for that source_id
        latest_status_subq = session.query(
            ScraperStatus.source_id,
            func.max(ScraperStatus.last_checked).label("max_last_checked")
        ).group_by(ScraperStatus.source_id).subquery()

        # Main query
        query = session.query(
            DataSource,
            prospect_count_subq.c.prospect_count,
            ScraperStatus 
        ).outerjoin(
            prospect_count_subq, DataSource.id == prospect_count_subq.c.source_id
        ).outerjoin(
            latest_status_subq, DataSource.id == latest_status_subq.c.source_id
        ).outerjoin(
            ScraperStatus, (ScraperStatus.source_id == latest_status_subq.c.source_id) & \
                           (ScraperStatus.last_checked == latest_status_subq.c.max_last_checked)
        )

        sources_data = query.all()
        
        result = [
            {
                "id": source.id,
                "name": source.name,
                "url": source.url,
                "description": source.description,
                "last_scraped": source.last_scraped.isoformat() if source.last_scraped else None,
                "prospectCount": p_count if p_count is not None else 0,
                "last_checked": status_rec.last_checked.isoformat() if status_rec and status_rec.last_checked else None,
                "status": status_rec.status if status_rec else "unknown"
            }
            for source, p_count, status_rec in sources_data
        ]
        
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error in get_data_sources: {str(e)}", exc_info=True)
        # Ensure no rollback here as it's a read operation primarily
        return jsonify({"status": "error", "message": "An internal error occurred processing your request."}), 500


@data_sources_bp.route('/<int:source_id>', methods=['PUT'])
def update_data_source(source_id):
    """Update a data source."""
    session = db.session
    try:
        # Validate input
        data = request.json
        if not data:
            raise ValidationError("No data provided")
        
        # Define updatable fields and their types/validation
        updatable_fields = {
            'name': str,
            'url': str,
            'description': str,
            'frequency': ['daily', 'weekly', 'monthly', 'manual', None] # None allows clearing
        }

        source = session.query(DataSource).filter(DataSource.id == source_id).first()
        if not source:
            raise NotFoundError(f"Data source with ID {source_id} not found")

        for field, value in data.items():
            if field in updatable_fields:
                if field == 'frequency' and value is not None and value not in updatable_fields['frequency']:
                    raise ValidationError(f"Invalid frequency. Must be one of: {', '.join(f for f in updatable_fields['frequency'] if f is not None)}")
                setattr(source, field, value)
            else:
                logger.warning(f"Attempted to update non-allowed field: {field}")
        
        session.commit()
        return jsonify({"status": "success", "message": "Data source updated", "data": source.to_dict()})
    except ValidationError as ve:
        # db.session.rollback() # Removed
        raise ve
    except Exception as e:
        # db.session.rollback() # Removed
        logger.error(f"Error in update_data_source: {str(e)}", exc_info=True) 
        raise DatabaseError("Failed to update data source")


@data_sources_bp.route('/', methods=['POST'])
def create_data_source():
    """Create a new data source."""
    session = db.session
    try:
        data = request.json
        if not data:
            raise ValidationError("No data provided for creating data source.")

        name = data.get('name')
        url = data.get('url')
        description = data.get('description')
        frequency = data.get('frequency', 'manual') # Default frequency to 'manual'

        if not name:
            raise ValidationError("Name is required for data source.")
        
        valid_frequencies = ['daily', 'weekly', 'monthly', 'manual']
        if frequency not in valid_frequencies:
            raise ValidationError(f"Invalid frequency. Must be one of: {', '.join(valid_frequencies)}")

        existing_source = session.query(DataSource).filter_by(name=name).first()
        if existing_source:
            raise ValidationError(f"Data source with name '{name}' already exists.")

        new_source = DataSource(
            name=name,
            url=url,
            description=description,
            frequency=frequency
        )
        session.add(new_source)
        session.commit()
        
        # Create an initial status record
        initial_status = ScraperStatus(
            source_id=new_source.id,
            status='pending', # Initial status
            details='Newly created data source, awaiting first scrape.'
        )
        session.add(initial_status)
        session.commit()

        return jsonify({"status": "success", "message": "Data source created", "data": new_source.to_dict()}), 201
    except ValidationError as ve:
        # db.session.rollback() # Removed
        raise ve
    except Exception as e:
        # db.session.rollback() # Removed
        logger.error(f"Error creating data source: {e}", exc_info=True)
        raise DatabaseError("Could not create data source")


@data_sources_bp.route('/<int:source_id>', methods=['DELETE'])
def delete_data_source(source_id):
    """Delete a data source and its related prospects and status records."""
    session = db.session
    try:
        source = session.query(DataSource).filter(DataSource.id == source_id).first()
        if not source:
            raise NotFoundError(f"Data source with ID {source_id} not found")
        
        session.delete(source)
        session.commit()
        return jsonify({"status": "success", "message": f"Data source {source_id} and related data deleted"})
    except NotFoundError as nfe:
        # db.session.rollback() # Removed
        raise nfe
    except Exception as e:
        # db.session.rollback() # Removed
        logger.error(f"Error deleting data source {source_id}: {e}", exc_info=True)
        raise DatabaseError(f"Could not delete data source {source_id}") 