import json
import time
import uuid
from pathlib import Path
import sys

from .models import DebateSession, DebateTurn, DebateResponse
from .citation_processor import extract_citations
from .model_client import ModelClient


class DebateManager:
    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(exist_ok=True)
        self.client = ModelClient()

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

    def start_debate(self, topic: str, model1: str, model2: str, model1_position: str, num_speeches: int = 16) -> DebateSession:
        """
        Create a new policy debate session.

        Args:
            topic: The debate topic
            model1: First model alias
            model2: Second model alias
            model1_position: Speaker position for model1 ("2A/1N" or "2N/1A")
            num_speeches: Number of speeches (8, 12, or 16)

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

        # Generate debate flow based on num_speeches
        # 8 speeches = constructives + cross-ex (first 12 items)
        # 12 speeches = constructives + cross-ex + 1NR/1AR (first 14 items)
        # 16 speeches = full policy debate (all items)
        debate_flow = self.policy_debate_flow[:num_speeches]

        session = DebateSession(
            session_id=session_id,
            topic=topic,
            debate_format="policy",
            models=models,
            speaker_positions=speaker_positions,
            current_speech_index=0,
            debate_flow=debate_flow,
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

        # Call model (either LM Studio or Anthropic API)
        result = self.client.chat(
            model_alias,
            context,
            temperature=session.settings["temperature"],
            max_tokens=session.settings["max_tokens"]
        )

        # Process response
        if result["success"]:
            # First strip thinking blocks
            clean_content = self._strip_thinking_blocks(result["content"])

            # Then format through Opus for consistency
            formatted_content = self._format_through_opus(clean_content, current_speech)

            # Extract citations
            content, citations = extract_citations(formatted_content)
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

        GLM-Flash outputs heavy thinking blocks - we need to find actual debate content.
        """
        import re

        # Pattern 1: Remove <think>...</think> blocks
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # Pattern 2: Remove everything before </think> tag
        cleaned = re.sub(r'^.*?</think>\s*', '', cleaned, flags=re.DOTALL)

        # Pattern 3: Find numbered thinking sections and locate actual content after them
        lines = cleaned.split('\n')

        # Find the LAST numbered thinking header (e.g., "5. **Final Output:**")
        thinking_header_pattern = r'^\s*\d+\.\s*\*\*[^*]+\*\*'
        last_thinking_header_index = -1

        for i, line in enumerate(lines):
            if re.match(thinking_header_pattern, line.strip()):
                last_thinking_header_index = i

        # If we found thinking headers, look for substantial content after the last one
        if last_thinking_header_index >= 0:
            # Look for the first substantial paragraph (>40 chars, not a bullet point)
            for i in range(last_thinking_header_index + 1, len(lines)):
                line = lines[i].strip()
                # Skip empty lines, bullets, and sub-headers
                if not line or line.startswith('*') or line.startswith('-') or re.match(r'^\d+\.', line):
                    continue
                # Found substantial content (likely the actual debate speech)
                if len(line) > 40:
                    cleaned = '\n'.join(lines[i:])
                    break
            else:
                # Fallback: take everything after the last thinking header
                cleaned = '\n'.join(lines[last_thinking_header_index + 1:])

        # Pattern 4: Remove any remaining asterisk bullets at the start
        cleaned = re.sub(r'^[\s*-]+', '', cleaned, flags=re.MULTILINE)

        return cleaned.strip()

    def _format_through_opus(self, raw_content: str, current_speech: dict) -> str:
        """
        Pass response through Claude Opus for consistent formatting.

        This ensures all responses (from any model) are clean, professional,
        and properly formatted for debate display.
        """
        speech_type = current_speech["type"]

        # Create formatting prompt based on speech type
        if speech_type == "constructive":
            instruction = (
                "Extract and format the debate argument. Remove any planning notes, "
                "thinking markers, or meta-commentary. Return ONLY the actual argument "
                "with clear paragraphs. Keep any [Source: ...] citations intact."
            )
        elif speech_type == "cx_question":
            instruction = (
                "Extract and format the cross-examination question. Remove any planning "
                "notes or strategic analysis. Return ONLY the actual question being asked, "
                "formatted as 1-2 clear, direct sentences."
            )
        elif speech_type == "cx_answer":
            instruction = (
                "Extract and format the cross-examination answer. Remove any planning "
                "notes. Return ONLY the actual answer, formatted clearly in 1-2 paragraphs."
            )
        else:  # rebuttal
            instruction = (
                "Extract and format the rebuttal. Remove any planning notes or analysis. "
                "Return ONLY the actual rebuttal arguments with clear paragraphs. "
                "Keep any [Source: ...] citations intact."
            )

        formatting_prompt = [
            {
                "role": "user",
                "content": f"{instruction}\n\nRaw content to format:\n\n{raw_content}"
            }
        ]

        # Call Opus for formatting (use short max_tokens for efficiency)
        result = self.client.chat(
            "claude-opus",
            formatting_prompt,
            temperature=0.3,
            max_tokens=1000
        )

        if result["success"]:
            return result["content"].strip()
        else:
            # If Opus formatting fails, return the cleaned content
            return raw_content

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
