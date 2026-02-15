import json
import time
import uuid
from pathlib import Path
import sys

# Add DALS to path for LMWorker import
sys.path.append('/Users/ssmithers/Desktop/CODE/dals')
from worker.lm_client import LMWorker

from .models import DebateSession, DebateTurn, DebateResponse
from .citation_processor import extract_citations


class DebateManager:
    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(exist_ok=True)
        self.worker = LMWorker()

        # Policy debate flow (1-minute speeches)
        self.policy_debate_flow = [
            {"speech": "1AC", "type": "constructive", "side": "aff", "speaker": "1A", "duration": 60},
            {"speech": "CX by 2N", "type": "cx_question", "side": "neg", "speaker": "2N", "duration": 60},
            {"speech": "Answer by 1A", "type": "cx_answer", "side": "aff", "speaker": "1A", "duration": 60},
            {"speech": "1NC", "type": "constructive", "side": "neg", "speaker": "1N", "duration": 60},
            {"speech": "CX by 1A", "type": "cx_question", "side": "aff", "speaker": "1A", "duration": 60},
            {"speech": "Answer by 1N", "type": "cx_answer", "side": "neg", "speaker": "1N", "duration": 60},
            {"speech": "2AC", "type": "constructive", "side": "aff", "speaker": "2A", "duration": 60},
            {"speech": "CX by 1N", "type": "cx_question", "side": "neg", "speaker": "1N", "duration": 60},
            {"speech": "Answer by 2A", "type": "cx_answer", "side": "aff", "speaker": "2A", "duration": 60},
            {"speech": "2NC", "type": "constructive", "side": "neg", "speaker": "2N", "duration": 60},
            {"speech": "CX by 2A", "type": "cx_question", "side": "aff", "speaker": "2A", "duration": 60},
            {"speech": "Answer by 2N", "type": "cx_answer", "side": "neg", "speaker": "2N", "duration": 60},
            {"speech": "1NR", "type": "rebuttal", "side": "neg", "speaker": "1N", "duration": 60},
            {"speech": "1AR", "type": "rebuttal", "side": "aff", "speaker": "1A", "duration": 60},
            {"speech": "2NR", "type": "rebuttal", "side": "neg", "speaker": "2N", "duration": 60},
            {"speech": "2AR", "type": "rebuttal", "side": "aff", "speaker": "2A", "duration": 60},
        ]

    def start_debate(self, topic: str, model1: str, model2: str, model1_position: str) -> DebateSession:
        """
        Create a new policy debate session.

        Args:
            topic: The debate topic
            model1: First model alias
            model2: Second model alias
            model1_position: Speaker position for model1 ("2A/1N" or "2N/1A")

        Returns:
            DebateSession object
        """
        session_id = str(uuid.uuid4())

        # Assign speaker positions and models
        # 2A/1N means: speaks 2nd for aff (2A), speaks 1st for neg (1N)
        # 2N/1A means: speaks 2nd for neg (2N), speaks 1st for aff (1A)
        if model1_position == "2A/1N":
            models = {"aff": model1, "neg": model2}
            speaker_positions = {"model1": "2A/1N", "model2": "2N/1A"}
        else:  # "2N/1A"
            models = {"aff": model2, "neg": model1}
            speaker_positions = {"model1": "2N/1A", "model2": "2A/1N"}

        session = DebateSession(
            session_id=session_id,
            topic=topic,
            debate_format="policy",
            models=models,
            speaker_positions=speaker_positions,
            current_speech_index=0,
            debate_flow=self.policy_debate_flow,
            turns=[],
            settings={"temperature": 0.3, "max_tokens": 512},  # ~1 min response
            status="active"
        )

        self._save_session(session)
        return session
    
    def execute_turn(self, session_id: str, moderator_message: str | None = None, is_interjection: bool = False) -> DebateTurn:
        """
        Execute one speech in the policy debate flow.

        Args:
            session_id: Session UUID
            moderator_message: Optional moderator interjection
            is_interjection: If True, don't advance speech index

        Returns:
            DebateTurn with single speaker's response
        """
        session = self._load_session(session_id)

        # Check if debate is complete
        if session.current_speech_index >= len(session.debate_flow):
            raise Exception("Debate is complete. No more speeches.")

        # Get current speech from flow
        current_speech = session.debate_flow[session.current_speech_index]
        turn_id = len(session.turns) + 1

        # Determine which model speaks
        speaker_position = current_speech["speaker"]
        side = current_speech["side"]
        model_alias = session.models[side]

        # Build context and system prompt
        context = self._build_context(session, side, current_speech, moderator_message)

        # Call LM Studio
        result = self.worker.chat(
            model_alias,
            context,
            temperature=session.settings["temperature"],
            max_tokens=session.settings["max_tokens"]
        )

        # Process response
        if result["success"]:
            clean_content = self._strip_thinking_blocks(result["content"])
            content, citations = extract_citations(clean_content)
        else:
            content = f"[ERROR: {result['error']}]"
            citations = []

        # Create turn
        turn = DebateTurn(
            turn_id=turn_id,
            speech_type=current_speech["type"],
            speech_name=current_speech["speech"],
            speaker_position=speaker_position,
            moderator_message=moderator_message,
            responses=[
                DebateResponse(
                    model_alias=model_alias,
                    stance=side,
                    speaker_position=speaker_position,
                    content=content,
                    citations=citations,
                    latency_ms=result["latency_ms"]
                )
            ],
            timestamp=time.time()
        )

        # Update session
        session.turns.append(turn)

        # Advance to next speech (unless it's an interjection)
        if not is_interjection:
            session.current_speech_index += 1

        self._save_session(session)

        return turn
    
    def end_topic(self, session_id: str) -> DebateSession:
        """Mark session as completed."""
        session = self._load_session(session_id)
        session.status = "completed"
        self._save_session(session)
        return session
    
    def _build_context(self, session: DebateSession, side: str, current_speech: dict, moderator_message: str | None) -> list[dict]:
        """
        Build message context for current speech in policy debate.

        Args:
            session: Current debate session
            side: "aff" or "neg"
            current_speech: Current speech from debate flow
            moderator_message: Optional moderator interjection
        """
        system_prompt = self._get_system_prompt(session.topic, side, current_speech, moderator_message)

        messages = [{"role": "system", "content": system_prompt}]

        # Add all previous turns
        for turn in session.turns:
            # Moderator interjections
            if turn.moderator_message and not turn.speech_type.startswith("cx"):
                messages.append({"role": "user", "content": f"[Moderator]: {turn.moderator_message}"})

            # Add the speech (same side = assistant, opposite = user)
            for response in turn.responses:
                if response.stance == side:
                    messages.append({"role": "assistant", "content": response.content})
                else:
                    # Label opponent's speech type for context
                    label = f"[{turn.speech_name}]" if turn.speech_type != "cx_answer" else ""
                    content = f"{label} {response.content}".strip()
                    messages.append({"role": "user", "content": content})

        return messages
    
    def _get_system_prompt(self, topic: str, side: str, current_speech: dict, moderator_message: str | None) -> str:
        """Generate system prompt based on speech type."""
        speech_type = current_speech["type"]
        speech_name = current_speech["speech"]
        side_label = "AFFIRMATIVE" if side == "aff" else "NEGATIVE"

        base = f"You are the {side_label} team in a policy debate on: '{topic}'.\n\n"
        base += f"Current Speech: {speech_name}\n\n"

        # CRITICAL: Explicitly forbid outputting reasoning process
        base += (
            "IMPORTANT: Output ONLY your debate speech. Do NOT output:\n"
            "- Your reasoning process or analysis steps\n"
            "- Planning notes like '1. Analyze the Request' or '2. Determine the Stance'\n"
            "- Meta-commentary about how you're constructing your argument\n"
            "- Any text before your actual debate content\n\n"
        )

        if speech_type == "constructive":
            base += (
                "This is a CONSTRUCTIVE speech. Deliver your arguments directly:\n"
                "- Introduce NEW arguments supporting your position\n"
                "- Present evidence and reasoning\n"
                "- Build your case with clear contentions\n"
                "- Cite sources using [Source: ...] format\n"
                "- Keep your response concise (aim for 3-5 key points)\n"
                "- Start immediately with your first argument\n"
            )

        elif speech_type == "cx_question":
            base += (
                "This is CROSS-EXAMINATION. Ask your question directly:\n"
                "- Ask ONE strategic question to challenge your opponent's case\n"
                "- Focus on exposing weaknesses or contradictions\n"
                "- Keep the question clear and direct\n"
                "- Do NOT answer - only ask the question\n"
                "- Start immediately with your question\n"
            )

        elif speech_type == "cx_answer":
            base += (
                "You are ANSWERING cross-examination. Respond directly:\n"
                "- Answer the question directly and briefly\n"
                "- Defend your position\n"
                "- Clarify any misunderstandings\n"
                "- Stay focused on the question asked\n"
                "- Start immediately with your answer\n"
            )

        elif speech_type == "rebuttal":
            base += (
                "This is a REBUTTAL speech. Deliver your rebuttal directly:\n"
                "- Refute your opponent's arguments\n"
                "- Extend your own arguments\n"
                "- Do NOT introduce brand new arguments\n"
                "- Focus on winning key issues in the debate\n"
                "- Cite sources using [Source: ...] format\n"
                "- Start immediately with your rebuttal\n"
            )

        if moderator_message:
            base += f"\n\n[MODERATOR INTERJECTION]: {moderator_message}\n"
            base += "Acknowledge this and adjust your speech accordingly.\n"

        return base
    
    def _strip_thinking_blocks(self, text: str) -> str:
        """
        Remove thinking blocks from model output.

        Some models leak their reasoning process in various formats:
        - <think>...</think> tags
        - Numbered reasoning steps (1. **Analyze**, 2. **Determine**, etc.)
        - Text before </think> tag
        """
        import re

        # Pattern 1: Remove <think>...</think> blocks (full tags)
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # Pattern 2: Remove everything before and including </think> tag
        cleaned = re.sub(r'^.*?</think>\s*', '', cleaned, flags=re.DOTALL)

        # Pattern 3: Remove numbered reasoning steps (e.g., "1. **Analyze the Request:**")
        # This catches models that output their thinking as numbered lists
        # Look for patterns like: "1. **Something:**" through "5. **Something:**" followed by actual content

        # Find if there's a numbered reasoning section followed by actual argumentative content
        lines = cleaned.split('\n')

        # Check if the response starts with numbered reasoning (1., 2., 3., etc.)
        if len(lines) > 0 and re.match(r'^\s*\d+\.\s*\*\*', lines[0]):
            # Find where the numbered reasoning ends and actual content begins
            # Usually the actual content starts after the last numbered item
            # or when we see a paragraph that doesn't start with a number

            actual_content_start = 0
            for i, line in enumerate(lines):
                # Skip empty lines and numbered items
                if not line.strip() or re.match(r'^\s*\d+\.\s*\*\*', line) or re.match(r'^\s*\*\s*\*', line):
                    continue
                # Found a line that's not part of the reasoning structure
                # Check if it looks like actual argumentative content
                if len(line.strip()) > 50 and not line.strip().startswith('*'):
                    actual_content_start = i
                    break

            if actual_content_start > 0:
                cleaned = '\n'.join(lines[actual_content_start:])

        # Pattern 4: Last resort - if still starts with "1. **Analyze" or similar, just take everything after "Drafting"
        if re.match(r'^\s*1\.\s*\*\*Analyze', cleaned, re.IGNORECASE):
            # Find content after "Drafting the Content" or "Final Output" or similar
            match = re.search(r'(?:Drafting|Final Output|Output Generation).*?:\s*\n\s*\n(.+)', cleaned, re.DOTALL | re.IGNORECASE)
            if match:
                cleaned = match.group(1)
            else:
                # If we can't find a clear marker, just take the last substantial paragraph
                paragraphs = [p.strip() for p in cleaned.split('\n\n') if len(p.strip()) > 100]
                if paragraphs:
                    cleaned = paragraphs[-1]

        # Remove any leading/trailing whitespace
        return cleaned.strip()

    def _save_session(self, session: DebateSession):
        """Save session to JSON file."""
        path = self.sessions_dir / f"{session.session_id}.json"
        with open(path, 'w') as f:
            json.dump(session.model_dump(), f, indent=2)
    
    def _load_session(self, session_id: str) -> DebateSession:
        """Load session from JSON file."""
        path = self.sessions_dir / f"{session_id}.json"
        with open(path) as f:
            data = json.load(f)
        return DebateSession(**data)
