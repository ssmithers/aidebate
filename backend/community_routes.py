from flask import Blueprint, request, jsonify
import sqlite3
from .community_db import add_topic, add_vote, get_ranked_topics, DB_FILE
from .debate_manager import DebateManager
from pathlib import Path

# Create Blueprint instead of new Flask app (integrates with existing app.py)
community_bp = Blueprint('community', __name__)

# Initialize debate manager for community debates
sessions_dir = Path(__file__).parent.parent / 'sessions'
debate_manager = DebateManager(sessions_dir)

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
    """
    Execute debate for top-voted topic.

    PATENT INTEGRATION: Starts debate using debate_manager and tracks
    topic_id for engagement system linkage (Claims #5, #6).

    Copyright (C) 2026 Stephen F Smithers
    """
    data = request.get_json()
    topic_id = data.get('topic_id')
    model1 = data.get('model1', 'glm-flash')  # Default models
    model2 = data.get('model2', 'qwen3-coder')
    model1_position = data.get('model1_position', '2A/1N')

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

    try:
        # Start debate with debate_manager
        session = debate_manager.start_debate(
            topic=target_topic['title'],
            model1=model1,
            model2=model2,
            model1_position=model1_position,
            num_speeches=18,
            topic_id=topic_id  # Link to community topic
        )

        # Execute all 18 speeches automatically
        for i in range(len(session.debate_flow)):
            turn = debate_manager.execute_turn(session.session_id)
            print(f"[DEBATE] Completed speech {i+1}/18: {turn.speech_name}")

        # End topic and save to engagement system
        completed_session = debate_manager.end_topic(session.session_id)

        # Update topic status to 'completed' in community DB
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE topics
                SET status = 'completed', last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (topic_id,))
            conn.commit()

        return jsonify({
            'session_id': completed_session.session_id,
            'topic': target_topic['title'],
            'status': 'completed',
            'total_speeches': len(completed_session.turns),
            'message': 'Debate completed and saved to engagement system'
        })

    except Exception as e:
        print(f"[EXECUTE ERROR] {e}")
        return jsonify({'error': f'Failed to execute debate: {str(e)}'}), 500

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
