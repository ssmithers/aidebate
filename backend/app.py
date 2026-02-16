from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import json
import sys
import os

# Add parent directory and DALS to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
sys.path.append('/Users/ssmithers/Desktop/CODE/dals')

from backend.debate_manager import DebateManager
from backend.community_routes import community_bp
from backend.community_db import create_tables
from backend.debate_engagement_routes import engagement_bp
from backend.debate_engagement_db import create_engagement_tables

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Initialize debate manager
sessions_dir = Path(__file__).parent.parent / 'sessions'
debate_manager = DebateManager(sessions_dir)

# Register community routes
app.register_blueprint(community_bp)

# Register engagement routes (Copyright 2026 Stephen F Smithers)
app.register_blueprint(engagement_bp)

# Initialize community database
create_tables()

# Initialize engagement tables (Patent Claims #5, #6 - Stephen F Smithers)
create_engagement_tables()

# Load models config
models_config_path = Path(__file__).parent.parent / 'config' / 'models.json'
with open(models_config_path) as f:
    models_config = json.load(f)


@app.route('/')
def index():
    """Serve main page."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/models', methods=['GET'])
def get_models():
    """Return available models (both local and API)."""
    models = []
    for alias, config in models_config['models'].items():
        # Skip embedding models
        if 'embed' in alias.lower():
            continue
        models.append({
            'alias': alias,
            'id': config['id'],
            'name': config.get('name', alias.replace('-', ' ').title()),
            'type': config.get('type', 'lm_studio')
        })
    return jsonify({'models': models})


@app.route('/api/debate/start', methods=['POST'])
def start_debate():
    """
    Start a new policy debate.

    Request: {topic, model1, model2, model1_position, num_speeches}
    Response: {session_id, topic, models, speaker_positions, current_speech}
    """
    data = request.json

    topic = data.get('topic')
    model1 = data.get('model1')
    model2 = data.get('model2')
    model1_position = data.get('model1_position', '2A/1N')
    num_speeches = data.get('num_speeches', 16)

    if not all([topic, model1, model2]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        session = debate_manager.start_debate(topic, model1, model2, model1_position, num_speeches)
        current_speech = session.debate_flow[session.current_speech_index]

        return jsonify({
            'session_id': session.session_id,
            'topic': session.topic,
            'models': session.models,
            'speaker_positions': session.speaker_positions,
            'debate_flow': session.debate_flow,
            'current_speech': current_speech
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/debate/turn', methods=['POST'])
def execute_turn():
    """
    Execute one speech in policy debate.

    Request: {session_id, moderator_message?, is_interjection?}
    Response: {turn_id, speech_type, speech_name, speaker_position, responses, next_speech}
    """
    data = request.json

    session_id = data.get('session_id')
    moderator_message = data.get('moderator_message')
    is_interjection = data.get('is_interjection', False)

    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400

    try:
        turn = debate_manager.execute_turn(session_id, moderator_message, is_interjection)

        # Get next speech info
        session = debate_manager._load_session(session_id)
        next_speech = None
        if session.current_speech_index < len(session.debate_flow):
            next_speech = session.debate_flow[session.current_speech_index]

        return jsonify({
            'turn_id': turn.turn_id,
            'speech_type': turn.speech_type,
            'speech_name': turn.speech_name,
            'speaker_position': turn.speaker_position,
            'responses': [r.model_dump() for r in turn.responses],
            'next_speech': next_speech,
            'debate_complete': session.current_speech_index >= len(session.debate_flow)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/debate/end-topic', methods=['POST'])
def end_topic():
    """
    End current debate topic.
    
    Request: {session_id}
    Response: {status, transcript}
    """
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400
    
    try:
        session = debate_manager.end_topic(session_id)
        return jsonify({
            'status': 'topic_ended',
            'transcript': [t.model_dump() for t in session.turns]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/debate/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """
    Get debate history.

    Response: {session_id, topic, turns}
    """
    try:
        session = debate_manager._load_session(session_id)
        return jsonify({
            'session_id': session.session_id,
            'topic': session.topic,
            'turns': [t.model_dump() for t in session.turns]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/api/debate/export/<session_id>', methods=['GET'])
def export_debate_markdown(session_id):
    """
    Export debate as beautifully formatted markdown transcript with summaries.

    Response: markdown text
    """
    try:
        session = debate_manager._load_session(session_id)
        from datetime import datetime

        # Header
        md = f"# 🎙️ Policy Debate Transcript\n\n"
        md += f"> **Topic**: {session.topic}\n\n"

        # Debate info table
        md += "## 📋 Debate Information\n\n"
        md += "| Category | Details |\n"
        md += "|----------|----------|\n"
        md += f"| **Format** | Policy Debate (18 speeches) |\n"
        md += f"| **Affirmative Team** | {session.models.get('aff', 'Unknown')} |\n"
        md += f"| **Negative Team** | {session.models.get('neg', 'Unknown')} |\n"
        md += f"| **Total Speeches** | {len(session.turns)} |\n"
        md += f"| **Status** | {session.status.title()} |\n\n"

        # Table of contents
        md += "## 📑 Table of Contents\n\n"
        md += "1. [Constructive Speeches](#constructive-speeches)\n"
        md += "2. [Cross-Examinations](#cross-examinations)\n"
        md += "3. [Rebuttals](#rebuttals)\n"
        md += "4. [Closing Arguments](#closing-arguments)\n"
        md += "5. [Summary](#summary)\n\n"

        md += "---\n\n"

        # Organize speeches by type
        constructives = []
        cross_exams = []
        rebuttals = []
        closings = []

        for turn in session.turns:
            if turn.speech_type == "constructive":
                constructives.append(turn)
            elif turn.speech_type in ["cx_question", "cx_answer"]:
                cross_exams.append(turn)
            elif turn.speech_type == "rebuttal":
                rebuttals.append(turn)
            elif turn.speech_type == "closing":
                closings.append(turn)

        # Constructive Speeches
        if constructives:
            md += "## 🏗️ Constructive Speeches\n\n"
            md += "_Opening arguments presenting each team's case_\n\n"
            for turn in constructives:
                md += format_speech_markdown(turn)
            md += "\n---\n\n"

        # Cross-Examinations
        if cross_exams:
            md += "## 🔍 Cross-Examinations\n\n"
            md += "_Strategic questioning to challenge opposing arguments_\n\n"
            for turn in cross_exams:
                md += format_speech_markdown(turn)
            md += "\n---\n\n"

        # Rebuttals
        if rebuttals:
            md += "## ⚔️ Rebuttals\n\n"
            md += "_Refutation of opposing arguments and extension of own case_\n\n"
            for turn in rebuttals:
                md += format_speech_markdown(turn)
            md += "\n---\n\n"

        # Closing Arguments (highlighted)
        if closings:
            md += "## 🎯 Closing Arguments\n\n"
            md += "_Final summaries and persuasive appeals_\n\n"
            for turn in closings:
                md += format_speech_markdown(turn, is_closing=True)
            md += "\n---\n\n"

        # Summary section with both closing arguments
        md += "## 📊 Summary\n\n"
        md += "### Final Positions\n\n"

        # Extract closing arguments
        aff_closing = None
        neg_closing = None

        for turn in closings:
            for response in turn.responses:
                if response.stance == "aff":
                    aff_closing = response.content
                elif response.stance == "neg":
                    neg_closing = response.content

        if aff_closing:
            md += "#### ✅ Affirmative Summary\n\n"
            md += f"> {aff_closing}\n\n"

        if neg_closing:
            md += "#### ❌ Negative Summary\n\n"
            md += f"> {neg_closing}\n\n"

        md += "---\n\n"
        md += "_Generated by AI Debate Simulator_\n"

        return md, 200, {'Content-Type': 'text/markdown; charset=utf-8'}

    except Exception as e:
        return jsonify({'error': str(e)}), 404


def format_speech_markdown(turn, is_closing=False):
    """Helper function to format a speech turn as markdown."""
    md = ""

    for response in turn.responses:
        speech_label = turn.speech_name
        stance_label = "Affirmative" if response.stance == "aff" else "Negative"
        stance_emoji = "✅" if response.stance == "aff" else "❌"

        # Use blockquote for closing arguments to make them stand out
        if is_closing:
            md += f"### {stance_emoji} {speech_label}\n\n"
            md += f"**{stance_label} Team** • Speaker {response.speaker_position} • Model: `{response.model_alias}`\n\n"
            md += f"> {response.content}\n\n"
        else:
            md += f"### {speech_label}\n\n"
            md += f"**{stance_label} Team** • Speaker {response.speaker_position} • Model: `{response.model_alias}`\n\n"
            md += f"{response.content}\n\n"

        # Citations
        if response.citations:
            md += "**📚 Sources**:\n"
            for i, citation in enumerate(response.citations, 1):
                md += f"{i}. {citation.get('text', 'Unknown source')}\n"
            md += "\n"

        md += "\n"

    return md


@app.route('/api/debate/usage/<session_id>', methods=['GET'])
def get_usage_report(session_id):
    """
    Get usage report for a debate session.

    Response: {usage_breakdown, totals, notes}
    """
    try:
        report = debate_manager.get_usage_report(session_id)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
