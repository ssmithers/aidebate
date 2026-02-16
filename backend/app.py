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
    Export debate as markdown transcript with legend.

    Response: markdown text
    """
    try:
        session = debate_manager._load_session(session_id)

        # Build markdown transcript
        md = f"# Policy Debate Transcript\n\n"
        md += f"**Topic**: {session.topic}\n\n"
        md += f"**Affirmative Model**: {session.models.get('aff', 'Unknown')}\n"
        md += f"**Negative Model**: {session.models.get('neg', 'Unknown')}\n\n"
        md += "---\n\n"

        # Legend
        md += "## Legend\n\n"
        md += "### Speech Types\n"
        md += "- **Constructive**: Opening arguments presenting the case\n"
        md += "- **Cross-Examination (CX)**: Question period where opponent challenges arguments\n"
        md += "- **Rebuttal**: Arguments refuting opponent's case\n"
        md += "- **Closing**: Final summary arguments\n\n"

        md += "### Speech Labels\n"
        md += "- **1AC**: First Affirmative Constructive\n"
        md += "- **1NC**: First Negative Constructive\n"
        md += "- **2AC**: Second Affirmative Constructive\n"
        md += "- **2NC**: Second Negative Constructive\n"
        md += "- **1NR**: First Negative Rebuttal\n"
        md += "- **1AR**: First Affirmative Rebuttal\n"
        md += "- **2NR**: Second Negative Rebuttal\n"
        md += "- **2AR**: Second Affirmative Rebuttal\n"
        md += "- **CX by [Speaker]**: Cross-examination question\n"
        md += "- **Answer by [Speaker]**: Cross-examination response\n\n"

        md += "### Speaker Positions\n"
        md += "- **1A/2A**: First/Second Affirmative Speaker\n"
        md += "- **1N/2N**: First/Second Negative Speaker\n\n"

        md += "---\n\n"
        md += "## Transcript\n\n"

        # Transcript
        for turn in session.turns:
            # Moderator message
            if turn.moderator_message:
                md += f"### [Moderator]\n\n"
                md += f"{turn.moderator_message}\n\n"

            # Speech
            for response in turn.responses:
                speech_label = turn.speech_name
                stance_label = "Affirmative" if response.stance == "aff" else "Negative"

                md += f"### {speech_label} ({stance_label})\n\n"
                md += f"**Speaker**: {response.speaker_position}\n"
                md += f"**Model**: {response.model_alias}\n\n"
                md += f"{response.content}\n\n"

                # Citations
                if response.citations:
                    md += "**Sources**:\n"
                    for i, citation in enumerate(response.citations, 1):
                        md += f"{i}. {citation.get('text', 'Unknown source')}\n"
                    md += "\n"

                md += "---\n\n"

        return md, 200, {'Content-Type': 'text/markdown; charset=utf-8'}

    except Exception as e:
        return jsonify({'error': str(e)}), 404


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
