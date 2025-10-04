# app/routes/feedback/routes.py
from flask import Blueprint, request
from app.extensions import db
from app.models import Feedback, FeedbackVote
from app.utils.decorators import token_required, roles_required
from app.utils.responses import success_response, error_response

feedback_bp = Blueprint("feedback", __name__, url_prefix="/feedback")


# ---------------------------
# SUBMIT FEEDBACK
# ---------------------------
@feedback_bp.route("/", methods=["POST"])
@token_required
def submit_feedback(current_user):
    """
    Submit new feedback
    ---
    tags:
      - Feedback
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [content]
          properties:
            content: {type: string}
            category: {type: string, default: general}
    responses:
      201:
        description: Feedback submitted successfully
      400:
        description: Content is required
    """
    """Submit new feedback"""
    data = request.get_json()
    if not data.get("content"):
        return error_response("Content is required", 400)

    feedback = Feedback(
        content=data["content"],
        category=data.get("category", "general"),
        user_id=current_user.id,
    )
    db.session.add(feedback)
    db.session.commit()

    return success_response(
        message="Feedback submitted successfully",
        status=201,
        data={
            "id": feedback.id,
            "content": feedback.content,
            "category": feedback.category,
            "user_id": feedback.user_id,
            "upvotes": 0,
            "downvotes": 0,
        },
    )


# ---------------------------
# LIST ALL FEEDBACK (Public)
# ---------------------------
@feedback_bp.route("/", methods=["GET"])
def list_feedback():
    """
    List all feedback
    ---
    tags:
      - Feedback
    responses:
      200:
        description: Feedback fetched successfully
    """
    """Fetch all feedback with votes"""
    feedback_list = Feedback.query.order_by(Feedback.created_at.desc()).all()
    data = []
    for f in feedback_list:
        data.append(
            {
                "id": f.id,
                "content": f.content,
                "category": f.category,
                "user_id": f.user_id,
                "upvotes": f.upvotes,
                "downvotes": f.downvotes,
                "created_at": f.created_at,
            }
        )

    return success_response(data, "Feedback fetched successfully")


# ---------------------------
# VOTE ON FEEDBACK
# ---------------------------
@feedback_bp.route("/<int:feedback_id>/vote", methods=["POST"])
@token_required
def vote_feedback(current_user, feedback_id):
    """
    Vote on feedback (upvote/downvote)
    ---
    tags:
      - Feedback
    parameters:
      - in: path
        name: feedback_id
        required: true
        type: integer
      - in: body
        name: body
        schema:
          type: object
          required: [vote]
          properties:
            vote:
              type: string
              enum: [upvote, downvote]
    responses:
      200:
        description: Vote recorded successfully
      400:
        description: Invalid vote value
      404:
        description: Feedback not found
    """
    """Vote on feedback (upvote/downvote)"""
    data = request.get_json()
    if not data.get("vote") or data["vote"] not in ["upvote", "downvote"]:
        return error_response("Vote must be 'upvote' or 'downvote'", 400)

    feedback = Feedback.query.get(feedback_id)
    if not feedback:
        return error_response("Feedback not found", 404)

    existing_vote = FeedbackVote.query.filter_by(
        user_id=current_user.id, feedback_id=feedback_id
    ).first()

    if existing_vote:
        existing_vote.vote_type = data["vote"]
    else:
        vote = FeedbackVote(
            user_id=current_user.id, feedback_id=feedback_id, vote_type=data["vote"]
        )
        db.session.add(vote)

    # Update counters
    feedback.upvotes = FeedbackVote.query.filter_by(
        feedback_id=feedback_id, vote_type="upvote"
    ).count()
    feedback.downvotes = FeedbackVote.query.filter_by(
        feedback_id=feedback_id, vote_type="downvote"
    ).count()

    db.session.commit()

    return success_response(
        message="Vote recorded successfully",
        data={
            "id": feedback.id,
            "upvotes": feedback.upvotes,
            "downvotes": feedback.downvotes,
        },
    )


# ---------------------------
# ADMIN: DELETE FEEDBACK
# ---------------------------
@feedback_bp.route("/<int:feedback_id>", methods=["DELETE"])
@token_required
@roles_required("admin")
def delete_feedback(current_user, feedback_id):
    """
    Delete feedback (Admin only)
    ---
    tags:
      - Feedback
    parameters:
      - in: path
        name: feedback_id
        required: true
        type: integer
    responses:
      200:
        description: Feedback deleted successfully
      404:
        description: Feedback not found
    """
    """Delete feedback (admin only)"""
    feedback = Feedback.query.get(feedback_id)
    if not feedback:
        return error_response("Feedback not found", 404)

    db.session.delete(feedback)
    db.session.commit()
    return success_response(message="Feedback deleted successfully")
