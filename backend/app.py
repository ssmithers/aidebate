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

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Initialize debate manager
sessions_dir = Path(__file__).parent.parent / 'sessions'
debate_manager = DebateManager(sessions_dir)

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

    Request: {topic, model1, model2, model1_position}
    Response: {session_id, topic, models, speaker_positions, current_speech}
    """
    data = request.json

    topic = data.get('topic')
    model1 = data.get('model1')
    model2 = data.get('model2')
    model1_position = data.get('model1_position', '2A/1N')

    if not all([topic, model1, model2]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        session = debate_manager.start_debate(topic, model1, model2, model1_position)
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
