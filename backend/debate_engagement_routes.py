"""
Debate Engagement API Routes
Copyright (C) 2026 Stephen F Smithers. All Rights Reserved.

PATENT-PROTECTED CODE - Automated Argumentation Processing System
This code implements proprietary REST API endpoints for:
- Real-Time Community Quality Assessment (Patent Claim #5)
- Temporal Engagement Metrics (Patent Claim #6)

NOTICE: This code contains trade secrets and confidential information
belonging to Stephen F Smithers. Unauthorized use, reproduction, or
distribution is strictly prohibited without written permission.

Author: Stephen F Smithers
Date: February 16, 2026
Repository: https://github.com/ssmithers/aidebate
"""

from flask import Blueprint, request, jsonify
from backend.debate_engagement_db import (
    create_engagement_tables,
    add_completed_debate,
    add_speech,
    vote_on_speech,
    add_comment,
    get_recent_debates,
    get_top_debates,
    get_debate_details,
    get_speech_comments,
    get_debate_comments
)

# Initialize Blueprint
# Copyright (C) 2026 Stephen F Smithers
engagement_bp = Blueprint('engagement', __name__)


@engagement_bp.route('/api/debates/recent', methods=['GET'])
def get_recent():
    """
    Get the most recent completed debates.

    Query params:
        limit (int): Number of debates to return (default 10)

    Returns:
        JSON array of debate objects

    Author: Stephen F Smithers
    """
    limit = request.args.get('limit', 10, type=int)
    debates = get_recent_debates(limit)
    return jsonify(debates)


@engagement_bp.route('/api/debates/top', methods=['GET'])
def get_top():
    """
    Get top debates by engagement score.

    PATENT CLAIM #6: Temporal Engagement Metrics
    Engagement = (pro_votes + con_votes + comments)

    Query params:
        limit (int): Number of debates to return (default 10)

    Returns:
        JSON array of debate objects ordered by engagement

    Proprietary Algorithm: Stephen F Smithers, 2026
    """
    limit = request.args.get('limit', 10, type=int)
    debates = get_top_debates(limit)
    return jsonify(debates)


@engagement_bp.route('/api/debates/<int:debate_id>', methods=['GET'])
def get_debate(debate_id: int):
    """
    Get full details of a specific debate.

    Path params:
        debate_id (int): ID of the debate

    Returns:
        JSON object with debate metadata, speeches, votes, and comments

    Copyright (C) 2026 Stephen F Smithers
    """
    debate = get_debate_details(debate_id)

    if not debate:
        return jsonify({'error': 'Debate not found'}), 404

    return jsonify(debate)


@engagement_bp.route('/api/debates/<int:debate_id>/speeches/<int:speech_id>/vote', methods=['POST'])
def vote_speech(debate_id: int, speech_id: int):
    """
    Vote on a specific speech.

    PATENT CLAIM #5: Real-Time Community Quality Assessment
    Enables users to vote on individual AI-generated arguments
    DURING the debate execution process.

    Path params:
        debate_id (int): ID of the debate
        speech_id (int): ID of the speech to vote on

    Request body:
        user_id (str): Anonymous user identifier
        vote_type (str): "up" or "down"

    Returns:
        Success message with updated vote counts

    Proprietary Feature: Stephen F Smithers, 2026
    """
    data = request.get_json()
    user_id = data.get('user_id')
    vote_type = data.get('vote_type')

    if not user_id or vote_type not in ['up', 'down']:
        return jsonify({'error': 'Invalid vote parameters'}), 400

    try:
        vote_on_speech(speech_id, user_id, vote_type)

        # Return updated debate details
        debate = get_debate_details(debate_id)
        return jsonify({
            'status': 'vote recorded',
            'debate': debate
        })
    except Exception as e:
        # Log error server-side (don't leak details to client)
        import logging
        logging.error(f"Vote error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to record vote'}), 500


@engagement_bp.route('/api/debates/<int:debate_id>/comments', methods=['POST'])
def add_debate_comment(debate_id: int):
    """
    Add a comment to a debate or specific speech.

    Path params:
        debate_id (int): ID of the debate

    Request body:
        user_id (str): Anonymous user identifier
        comment_text (str): Comment content
        speech_id (int, optional): ID of speech being commented on
        parent_id (int, optional): ID of parent comment for threading

    Returns:
        Comment ID and success message

    Author: Stephen F Smithers
    """
    data = request.get_json()
    user_id = data.get('user_id')
    comment_text = data.get('comment_text')
    speech_id = data.get('speech_id')
    parent_id = data.get('parent_id')

    if not user_id or not comment_text:
        return jsonify({'error': 'user_id and comment_text required'}), 400

    try:
        comment_id = add_comment(
            debate_id,
            user_id,
            comment_text,
            speech_id,
            parent_id
        )
        return jsonify({
            'status': 'comment added',
            'comment_id': comment_id
        })
    except Exception as e:
        # Log error server-side (don't leak details to client)
        import logging
        logging.error(f"Vote error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to record vote'}), 500


@engagement_bp.route('/api/debates/<int:debate_id>/comments', methods=['GET'])
def get_comments(debate_id: int):
    """
    Get all comments for a debate.

    Path params:
        debate_id (int): ID of the debate

    Query params:
        speech_id (int, optional): Filter by specific speech

    Returns:
        JSON array of comment objects

    Copyright (C) 2026 Stephen F Smithers
    """
    speech_id = request.args.get('speech_id', type=int)

    if speech_id:
        comments = get_speech_comments(speech_id)
    else:
        comments = get_debate_comments(debate_id)

    return jsonify(comments)


# Removed public /api/debates/init endpoint for security
# Tables are initialized at app startup in app.py

# Export blueprint for registration
# Copyright (C) 2026 Stephen F Smithers
__all__ = ['engagement_bp']
