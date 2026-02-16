"""
Judge API Routes
Copyright (C) 2026 Stephen F Smithers. All Rights Reserved.

REST API for AI debate judging system.

Author: Stephen F Smithers
Date: February 16, 2026
"""

from flask import Blueprint, request, jsonify
import json
from pathlib import Path
from debate_judge import judge_debate, get_judgments_for_debate

judge_bp = Blueprint('judge', __name__)
sessions_dir = Path(__file__).parent.parent / 'sessions'


@judge_bp.route('/api/debates/<int:debate_id>/judge', methods=['POST'])
def request_judgment(debate_id):
    """
    Request AI judgment for a completed debate.

    Request body:
        {
            "judge_model": "claude-opus-4-6"  // optional, defaults to Opus 4.6
        }

    Returns:
        Judgment JSON with winner, confidence, reasoning, scores

    Author: Stephen F Smithers
    """
    try:
        data = request.get_json() or {}
        judge_model = data.get('judge_model', 'claude-opus-4-6')

        # Get session_id for this debate
        import sqlite3
        db_file = Path(__file__).parent.parent / 'community.db'
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id FROM completed_debates WHERE id = ?",
                (debate_id,)
            )
            row = cursor.fetchone()
            if not row or not row[0]:
                return jsonify({'error': 'Debate not found or no session_id'}), 404

            session_id = row[0]

        # Load session data
        session_file = sessions_dir / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({'error': 'Session file not found'}), 404

        with open(session_file) as f:
            session_data = json.load(f)

        # Request judgment
        judgment = judge_debate(debate_id, session_data, judge_model)

        return jsonify(judgment), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to judge debate: {str(e)}'}), 500


@judge_bp.route('/api/debates/<int:debate_id>/judgments', methods=['GET'])
def get_judgments(debate_id):
    """
    Get all judgments for a debate (supports multiple judges).

    Returns:
        JSON array of judgment objects

    Author: Stephen F Smithers
    """
    try:
        judgments = get_judgments_for_debate(debate_id)
        return jsonify(judgments), 200
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve judgments: {str(e)}'}), 500
