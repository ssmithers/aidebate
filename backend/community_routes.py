from flask import Blueprint, request, jsonify
import sqlite3
from .community_db import add_topic, add_vote, get_ranked_topics, DB_FILE
from pathlib import Path

# Create Blueprint instead of new Flask app (integrates with existing app.py)
community_bp = Blueprint('community', __name__)

@community_bp.route('/api/community/suggest', methods=['POST'])
def suggest():
    """Accept topic suggestion from user"""
    data = request.get_json()
    title = data.get('title')

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    # Calculate complexity score (simple word count for now)
    complexity_score = len(title.split())

    # Add topic to database
    topic_id = add_topic(
        title=title,
        embedding_vector=None,  # TODO: Add actual embedding generation
        consensus_score=0.0,
        status='active',
        complexity_score=complexity_score
    )

    return jsonify({'topic_id': topic_id, 'title': title})

@community_bp.route('/api/community/vote', methods=['POST'])
def vote():
    """Record user vote and update consensus score"""
    data = request.get_json()
    topic_id = data.get('topic_id')
    user_id = data.get('user_id')
    vote_type = data.get('vote_type')  # 'up' or 'down'

    if not all([topic_id, user_id, vote_type]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Add vote to database
    add_vote(topic_id, user_id, vote_type)

    # Update consensus score using weighted average
    update_consensus_score(topic_id)

    return jsonify({'status': 'vote recorded'})

@community_bp.route('/api/community/topics', methods=['GET'])
def topics():
    """Get ranked topics by consensus score"""
    limit = request.args.get('limit', default=10, type=int)
    topics = get_ranked_topics(limit=limit)
    return jsonify(topics)

@community_bp.route('/api/community/execute', methods=['POST'])
def execute():
    """Execute debate for top-voted topic"""
    data = request.get_json()
    topic_id = data.get('topic_id')

    if not topic_id:
        return jsonify({'error': 'Topic ID required'}), 400

    # Get topic details
    topics = get_ranked_topics(limit=100)
    target_topic = next((t for t in topics if t.get('id') == topic_id), None)

    if not target_topic:
        return jsonify({'error': 'Topic not found'}), 404

    # Check consensus threshold
    if target_topic.get('consensus_score', 0) <= 0.5:
        return jsonify({'error': 'Consensus score too low (must be > 0.5)'}), 400

    # Return job_id for now (full debate integration coming next)
    return jsonify({
        'job_id': f'debate_{topic_id}',
        'topic': target_topic['title'],
        'status': 'pending'
    })

def update_consensus_score(topic_id: int):
    """Update consensus score using weighted average of votes"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Count up and down votes
        cursor.execute("""
            SELECT vote_type, COUNT(*) as count
            FROM votes
            WHERE topic_id = ?
            GROUP BY vote_type
        """, (topic_id,))

        votes = dict(cursor.fetchall())
        up_votes = votes.get('up', 0)
        down_votes = votes.get('down', 0)

        # Calculate weighted consensus score (0-1 range)
        total_votes = up_votes + down_votes
        if total_votes == 0:
            consensus_score = 0.0
        else:
            consensus_score = up_votes / total_votes

        # Update topic consensus score
        cursor.execute("""
            UPDATE topics
            SET consensus_score = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (consensus_score, topic_id))

        conn.commit()
