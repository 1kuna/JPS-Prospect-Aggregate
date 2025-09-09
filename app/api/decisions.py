"""Go/No-Go Decision API endpoints for JPS Prospect Aggregate.

Handles user decisions on prospects for company preferences.
"""

import datetime
from datetime import timezone
UTC = timezone.utc

from flask import request, session
from sqlalchemy import desc, func

from app.api.factory import (
    api_route,
    create_blueprint,
    error_response,
    success_response,
)
from app.database.models import GoNoGoDecision, Prospect, db
from app.utils.user_utils import get_user_by_id, get_user_data_dict, get_users_by_ids

decisions_bp, logger = create_blueprint("decisions", "/api/decisions")


@api_route(decisions_bp, "/", methods=["POST"], auth="login")
def create_decision():
    """Create or update a Go/No-Go decision for a prospect."""
    try:
        data = request.get_json()
        if not data:
            return error_response(400, "Request body is required")

        prospect_id = data.get("prospect_id")
        decision = data.get("decision", "").strip().lower()
        reason_raw = data.get("reason")
        if reason_raw is not None:
            reason = reason_raw.strip() if reason_raw.strip() else None
        else:
            reason = None

        if not prospect_id or not decision:
            return error_response(400, "prospect_id and decision are required")

        if decision not in ["go", "no-go"]:
            return error_response(400, 'Decision must be either "go" or "no-go"')

        # Verify prospect exists
        prospect = db.session.query(Prospect).filter_by(id=prospect_id).first()
        if not prospect:
            return error_response(404, f"Prospect with ID {prospect_id} not found")

        user_id = session.get("user_id")

        # Check if user already has a decision for this prospect
        existing_decision = (
            db.session.query(GoNoGoDecision)
            .filter_by(prospect_id=prospect_id, user_id=user_id)
            .first()
        )

        if existing_decision:
            # Update existing decision
            existing_decision.decision = decision
            existing_decision.reason = reason
            existing_decision.updated_at = datetime.datetime.now(UTC)
            logger.info(
                f"Updated decision for prospect {prospect_id} by user {user_id}: {decision}"
            )
        else:
            # Create new decision
            new_decision = GoNoGoDecision(
                prospect_id=prospect_id, user_id=user_id, decision=decision, reason=reason
            )
            db.session.add(new_decision)
            existing_decision = new_decision
            logger.info(
                f"Created decision for prospect {prospect_id} by user {user_id}: {decision}"
            )

        db.session.commit()

        return success_response(
            data={"decision": existing_decision.to_dict()},
            message=f"Decision {'updated' if existing_decision.id else 'created'} successfully"
        )

    except Exception as e:
        logger.error(f"Error creating/updating decision: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to save decision")


@api_route(decisions_bp, "/prospect/<prospect_id>", methods=["GET"], auth="login")
def get_decisions_for_prospect(prospect_id):
    """Get all decisions for a specific prospect."""
    try:
        # Verify prospect exists
        prospect = db.session.query(Prospect).filter_by(id=prospect_id).first()
        if not prospect:
            return error_response(404, f"Prospect with ID {prospect_id} not found")

        # Get all decisions for this prospect
        decisions = (
            db.session.query(GoNoGoDecision)
            .filter_by(prospect_id=prospect_id)
            .order_by(desc(GoNoGoDecision.created_at))
            .all()
        )

        # Get user data for all decisions
        user_ids = [d.user_id for d in decisions]
        users_data = get_users_by_ids(user_ids)

        # Build response with user information
        decision_data = []
        for decision in decisions:
            user_data = get_user_data_dict(users_data.get(decision.user_id))
            decision_dict = decision.to_dict(include_user=True, user_data=user_data)
            decision_data.append(decision_dict)

        return success_response(
            data={
                "prospect_id": prospect_id,
                "decisions": decision_data,
                "total_decisions": len(decisions),
            }
        )

    except Exception as e:
        logger.error(
            f"Error getting decisions for prospect {prospect_id}: {str(e)}",
            exc_info=True,
        )
        return error_response(500, "Failed to get decisions")


@api_route(decisions_bp, "/user", methods=["GET"], auth="login")
def get_user_decisions():
    """Get all decisions made by the current user."""
    try:
        user_id = session.get("user_id")

        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        # Get filter parameters
        decision_filter = request.args.get("decision")  # 'go', 'no-go', or None for all

        # Build query
        query = db.session.query(GoNoGoDecision).filter_by(user_id=user_id)

        if decision_filter and decision_filter in ["go", "no-go"]:
            query = query.filter(GoNoGoDecision.decision == decision_filter)

        query = query.order_by(desc(GoNoGoDecision.created_at))

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        decisions = query.offset((page - 1) * per_page).limit(per_page).all()

        # Get prospect data for all decisions
        prospect_ids = [d.prospect_id for d in decisions]
        prospects = (
            db.session.query(Prospect).filter(Prospect.id.in_(prospect_ids)).all()
        )
        prospects_dict = {p.id: p for p in prospects}

        # Build response data
        decision_data = []
        for decision in decisions:
            decision_dict = decision.to_dict()
            # Add basic prospect info
            prospect = prospects_dict.get(decision.prospect_id)
            if prospect:
                decision_dict["prospect"] = {
                    "id": prospect.id,
                    "title": prospect.title,
                    "agency": prospect.agency,
                    "naics": prospect.naics,
                    "place_city": prospect.place_city,
                    "place_state": prospect.place_state,
                }
            decision_data.append(decision_dict)

        return success_response(
            data={
                "decisions": decision_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting user decisions: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get user decisions")


@api_route(decisions_bp, "/stats", methods=["GET"], auth="login")
def get_decision_stats():
    """Get statistics about the current user's decisions."""
    try:
        user_id = session.get("user_id")

        # Get counts
        total_decisions = (
            db.session.query(func.count(GoNoGoDecision.id))
            .filter_by(user_id=user_id)
            .scalar()
        )
        go_decisions = (
            db.session.query(func.count(GoNoGoDecision.id))
            .filter_by(user_id=user_id, decision="go")
            .scalar()
        )
        nogo_decisions = (
            db.session.query(func.count(GoNoGoDecision.id))
            .filter_by(user_id=user_id, decision="no-go")
            .scalar()
        )

        # Get recent activity (last 7 days)
        seven_days_ago = datetime.datetime.now(UTC) - datetime.timedelta(days=7)
        recent_decisions = (
            db.session.query(func.count(GoNoGoDecision.id))
            .filter(
                GoNoGoDecision.user_id == user_id,
                GoNoGoDecision.created_at >= seven_days_ago,
            )
            .scalar()
        )

        # Get top agencies for go decisions
        top_go_agencies = (
            db.session.query(Prospect.agency, func.count(GoNoGoDecision.id).label("count"))
            .join(GoNoGoDecision, Prospect.id == GoNoGoDecision.prospect_id)
            .filter(GoNoGoDecision.user_id == user_id, GoNoGoDecision.decision == "go")
            .group_by(Prospect.agency)
            .order_by(desc("count"))
            .limit(5)
            .all()
        )

        # Get top NAICS codes for go decisions
        top_go_naics = (
            db.session.query(Prospect.naics, func.count(GoNoGoDecision.id).label("count"))
            .join(GoNoGoDecision, Prospect.id == GoNoGoDecision.prospect_id)
            .filter(
                GoNoGoDecision.user_id == user_id,
                GoNoGoDecision.decision == "go",
                Prospect.naics.isnot(None),
            )
            .group_by(Prospect.naics)
            .order_by(desc("count"))
            .limit(5)
            .all()
        )

        return success_response(
            data={
                "total_decisions": total_decisions,
                "go_decisions": go_decisions,
                "nogo_decisions": nogo_decisions,
                "go_percentage": round((go_decisions / total_decisions) * 100, 1)
                if total_decisions > 0
                else 0,
                "recent_decisions_7d": recent_decisions,
                "top_go_agencies": [{"agency": agency, "count": count} for agency, count in top_go_agencies],
                "top_go_naics": [{"naics": naics, "count": count} for naics, count in top_go_naics],
            }
        )

    except Exception as e:
        logger.error(f"Error getting decision stats: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get decision statistics")


@api_route(decisions_bp, "/<int:decision_id>", methods=["DELETE"], auth="login")
def delete_decision(decision_id):
    """Delete a specific decision (user can only delete their own)."""
    try:
        user_id = session.get("user_id")

        # Get the decision
        decision = db.session.query(GoNoGoDecision).filter_by(id=decision_id).first()
        if not decision:
            return error_response(404, "Decision not found")

        # Check if user owns this decision
        if decision.user_id != user_id:
            return error_response(403, "You can only delete your own decisions")

        # Delete the decision
        db.session.delete(decision)
        db.session.commit()

        logger.info(f"Deleted decision {decision_id} by user {user_id}")

        return success_response(message="Decision deleted successfully")

    except Exception as e:
        logger.error(f"Error deleting decision {decision_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to delete decision")