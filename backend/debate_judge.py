"""
AI Debate Judge System
Copyright (C) 2026 Stephen F Smithers. All Rights Reserved.

Objective AI evaluation of debate quality and winner determination.
Designed to support multiple judge models for unbiased assessment.

Author: Stephen F Smithers
Date: February 16, 2026
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
import anthropic
import os

DB_FILE = Path(__file__).parent.parent / 'community.db'


def get_judge_prompt(debate_transcript: str) -> str:
    """
    Constructs the system prompt for the debate judge.

    The judge evaluates debates on objective criteria:
    - Argument Quality (clarity, logic, structure)
    - Evidence Usage (citations, factual support)
    - Rebuttal Effectiveness (addressing opponent's points)
    - Cross-Examination (strategic questioning, responses)
    - Closing Impact (persuasiveness, summary strength)

    Returns structured JSON with winner, confidence, reasoning, and scores.
    """
    return f"""You are an expert debate judge evaluating a policy debate. Your role is to objectively assess which side presented the stronger overall case.

DEBATE TRANSCRIPT:
{debate_transcript}

EVALUATION CRITERIA (score each 0-10):
1. **Argument Quality**: Clarity, logical structure, coherence
2. **Evidence Usage**: Citations, factual support, credibility
3. **Rebuttal Effectiveness**: Addressing opponent's points, defensive strength
4. **Cross-Examination**: Strategic questioning, handling of CX
5. **Closing Impact**: Persuasiveness of final arguments, summary strength

INSTRUCTIONS:
- Be completely objective - judge arguments, not topics
- Consider both sides fairly
- Base judgment on debate performance, not external beliefs
- A "tie" is acceptable if truly evenly matched

Respond with ONLY valid JSON in this exact format:
{{
    "winner": "pro" | "con" | "tie",
    "confidence": 0.85,
    "reasoning": "Detailed explanation of your decision (2-3 paragraphs)",
    "criteria_scores": {{
        "argument_quality": {{"pro": 8, "con": 7}},
        "evidence_usage": {{"pro": 7, "con": 8}},
        "rebuttal_effectiveness": {{"pro": 9, "con": 6}},
        "cross_examination": {{"pro": 7, "con": 7}},
        "closing_impact": {{"pro": 8, "con": 7}}
    }},
    "total_scores": {{"pro": 39, "con": 35}}
}}"""


def judge_debate(
    debate_id: int,
    session_data: Dict[str, Any],
    judge_model: str = "claude-opus-4-6"
) -> Dict[str, Any]:
    """
    Sends debate to AI judge for evaluation.

    Args:
        debate_id: ID of the completed debate
        session_data: Full debate session data from JSON file
        judge_model: Model to use as judge (default: claude-opus-4-6)

    Returns:
        Judgment dictionary with winner, confidence, reasoning, scores

    Author: Stephen F Smithers
    """
    # Build debate transcript
    transcript = build_transcript(session_data)

    # Get judge evaluation based on model
    if judge_model.startswith("claude"):
        judgment = judge_with_claude(transcript, judge_model)
    else:
        raise ValueError(f"Unsupported judge model: {judge_model}")

    # Save judgment to database
    save_judgment(debate_id, judge_model, judgment)

    return judgment


def build_transcript(session_data: Dict[str, Any]) -> str:
    """
    Builds a clean debate transcript for judge evaluation.

    Args:
        session_data: Full debate session data

    Returns:
        Formatted transcript string with all speeches
    """
    transcript = f"TOPIC: {session_data['topic']}\n\n"
    transcript += f"AFFIRMATIVE: {session_data['models'].get('aff', 'Unknown')}\n"
    transcript += f"NEGATIVE: {session_data['models'].get('neg', 'Unknown')}\n\n"
    transcript += "=" * 60 + "\n\n"

    for turn in session_data.get('turns', []):
        for response in turn.get('responses', []):
            speech_name = response.get('speech_name', 'Unknown')
            content = response.get('content', '')
            stance = response.get('stance', '').upper()

            transcript += f"[{speech_name} - {stance}]\n"
            transcript += f"{content}\n\n"
            transcript += "-" * 60 + "\n\n"

    return transcript


def judge_with_claude(transcript: str, model: str) -> Dict[str, Any]:
    """
    Uses Claude (Opus 4.6) to judge the debate.

    Args:
        transcript: Full debate transcript
        model: Claude model ID (e.g., "claude-opus-4-6")

    Returns:
        Judgment dictionary

    Author: Stephen F Smithers
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = get_judge_prompt(transcript)

    # Call Claude API
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0.3,  # Lower temperature for objective evaluation
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    # Parse JSON response
    content = response.content[0].text

    # Extract JSON from response (in case there's extra text)
    try:
        # Try to find JSON block
        if '```json' in content:
            json_start = content.find('```json') + 7
            json_end = content.find('```', json_start)
            content = content[json_start:json_end].strip()
        elif '```' in content:
            json_start = content.find('```') + 3
            json_end = content.find('```', json_start)
            content = content[json_start:json_end].strip()

        judgment = json.loads(content)
        return judgment
    except json.JSONDecodeError as e:
        raise ValueError(f"Judge returned invalid JSON: {e}\nContent: {content}")


def save_judgment(
    debate_id: int,
    judge_model: str,
    judgment: Dict[str, Any]
) -> int:
    """
    Saves judgment to database.

    Args:
        debate_id: ID of the debate
        judge_model: Model that judged
        judgment: Judgment data

    Returns:
        Judgment ID

    Author: Stephen F Smithers
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO judgments
            (debate_id, judge_model, winner, confidence, reasoning, criteria_scores)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            debate_id,
            judge_model,
            judgment['winner'],
            judgment.get('confidence', 0.0),
            judgment.get('reasoning', ''),
            json.dumps(judgment.get('criteria_scores', {}))
        ))
        conn.commit()
        return cursor.lastrowid


def get_judgments_for_debate(debate_id: int) -> list:
    """
    Retrieves all judgments for a debate (supports multiple judges).

    Args:
        debate_id: ID of the debate

    Returns:
        List of judgment dictionaries
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id, judge_model, winner, confidence,
                reasoning, criteria_scores, judged_at
            FROM judgments
            WHERE debate_id = ?
            ORDER BY judged_at DESC
        """, (debate_id,))

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        judgments = []
        for row in rows:
            judgment = dict(zip(columns, row))
            # Parse JSON criteria_scores
            if judgment['criteria_scores']:
                judgment['criteria_scores'] = json.loads(judgment['criteria_scores'])
            judgments.append(judgment)

        return judgments
