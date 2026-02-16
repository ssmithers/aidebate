import json
import time
import uuid
from pathlib import Path
from typing import Optional
import sys

from .models import DebateSession, DebateTurn, DebateResponse, ModelUsage
from .citation_processor import extract_citations
from .model_client import ModelClient

# Engagement system integration (Copyright 2026 Stephen F Smithers)
from .debate_engagement_db import (
    add_completed_debate,
    add_speech,
    create_engagement_tables
)


class DebateManager:
    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(exist_ok=True)
        self.client = ModelClient()

        # Policy debate flow (1-minute speeches) + closing arguments
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
            {"speech": "Affirmative Closing", "type": "closing", "side": "aff", "speaker": "2A", "duration": 60},
            {"speech": "Negative Closing", "type": "closing", "side": "neg", "speaker": "2N", "duration": 60},
        ]

    def start_debate(self, topic: str, model1: str, model2: str, model1_position: str, num_speeches: int = 18, topic_id: int = 0) -> DebateSession:
        """
        Create a new policy debate session.

        Args:
            topic: The debate topic
            model1: First model alias
            model2: Second model alias
            model1_position: Speaker position for model1 ("2A/1N" or "2N/1A")
            num_speeches: Number of speeches (ignored - always uses 18: full policy debate + closing arguments)
            topic_id: Community topic ID (0 for manual debates)

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

        # Always use full 16-speech policy debate flow
        debate_flow = self.policy_debate_flow

        session = DebateSession(
            session_id=session_id,
            topic=topic,
            debate_format="policy",
            models=models,
            speaker_positions=speaker_positions,
            current_speech_index=0,
            debate_flow=debate_flow,
            turns=[],
            settings={"temperature": 0.3, "max_tokens": 16384},  # Allow full-length arguments
            status="active",
            topic_id=topic_id  # Store for engagement system integration
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

        # Log debate content generation usage
        model_config = self.client.models.get(model_alias, {})
        model_type = model_config.get("type", "unknown")
        usage = result.get("usage", {})

        session.usage_log.append(ModelUsage(
            model=model_config.get("id", model_alias),
            model_type=model_type,
            purpose="debate_content",
            speech_name=current_speech["speech"],
            input_tokens=usage.get("input_tokens", 0) if usage else 0,
            output_tokens=usage.get("output_tokens", 0) if usage else 0,
            latency_ms=result.get("latency_ms", 0)
        ))

        # Process response
        if result["success"]:
            # DEBUG: Log raw output from model
            raw_output = result["content"]
            print(f"\n[DEBUG] Raw output from {model_alias} ({current_speech['speech']}):")
            print(f"Length: {len(raw_output)} chars")
            print(f"First 200 chars: {raw_output[:200]}")
            print(f"Last 200 chars: {raw_output[-200:]}\n")

            # Use Haiku for formatting (cheap, effective, uses subscription credits first)
            # 60x cheaper than Opus, perfect for cleaning tasks
            formatted_content, formatting_usage = self._format_with_haiku(raw_output, current_speech)

            # DEBUG: Log after formatting
            print(f"[DEBUG] After formatting:")
            print(f"Length: {len(formatted_content)} chars")
            print(f"Content: {formatted_content[:200]}\n")

            # Log formatting usage
            if formatting_usage:
                session.usage_log.append(formatting_usage)

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
        """
        Mark session as completed and save to engagement system.

        PATENT INTEGRATION: Saves debate to engagement tables for
        community voting and temporal metrics (Claims #5, #6).

        Copyright (C) 2026 Stephen F Smithers
        """
        session = self._load_session(session_id)
        session.status = "completed"

        # Save to engagement system for community voting
        try:
            # Get topic_id if available (otherwise use 0 for manual debates)
            topic_id = getattr(session, 'topic_id', 0)

            # Create debate record
            debate_id = add_completed_debate(
                topic_id=topic_id,
                job_id=0,  # No job_id for manual debates
                pro_model=session.models.get('aff', 'unknown'),
                con_model=session.models.get('neg', 'unknown')
            )

            # Save all speeches to engagement system
            for turn in session.turns:
                for response in turn.responses:
                    add_speech(
                        debate_id=debate_id,
                        speech_type=turn.speech_name,
                        side=response.stance,
                        content=response.content
                    )

            print(f"[ENGAGEMENT] Saved debate {debate_id} with {len(session.turns)} speeches")
        except Exception as e:
            print(f"[ENGAGEMENT ERROR] Failed to save debate: {e}")

        self._save_session(session)
        return session

    def get_usage_report(self, session_id: str) -> dict:
        """
        Generate a detailed usage report for the debate.

        Returns:
            dict with usage breakdown by model, purpose, and credit source
        """
        session = self._load_session(session_id)

        # Aggregate usage by model and purpose
        usage_by_model = {}
        total_anthropic_input = 0
        total_anthropic_output = 0
        total_local_calls = 0

        for usage in session.usage_log:
            key = f"{usage.model}_{usage.purpose}"

            if key not in usage_by_model:
                usage_by_model[key] = {
                    "model": usage.model,
                    "model_type": usage.model_type,
                    "purpose": usage.purpose,
                    "speeches": [],
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_calls": 0
                }

            usage_by_model[key]["speeches"].append(usage.speech_name)
            usage_by_model[key]["total_input_tokens"] += usage.input_tokens
            usage_by_model[key]["total_output_tokens"] += usage.output_tokens
            usage_by_model[key]["total_calls"] += 1

            # Track totals
            if usage.model_type == "anthropic":
                total_anthropic_input += usage.input_tokens
                total_anthropic_output += usage.output_tokens
            elif usage.model_type == "lm_studio":
                total_local_calls += 1

        # Calculate costs (API key rates - actual cost depends on subscription usage)
        cost_rates = {
            "claude-opus-4-6": {"input": 15.00, "output": 75.00},  # per 1M tokens
            "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
            "claude-haiku-4-5": {"input": 0.25, "output": 1.25}
        }

        total_estimated_cost = 0
        for usage_data in usage_by_model.values():
            if usage_data["model_type"] == "anthropic":
                model = usage_data["model"]
                rates = cost_rates.get(model, {"input": 0, "output": 0})

                input_cost = (usage_data["total_input_tokens"] / 1_000_000) * rates["input"]
                output_cost = (usage_data["total_output_tokens"] / 1_000_000) * rates["output"]

                usage_data["estimated_cost"] = input_cost + output_cost
                total_estimated_cost += usage_data["estimated_cost"]
            else:
                usage_data["estimated_cost"] = 0.0

        return {
            "session_id": session_id,
            "topic": session.topic,
            "total_speeches": len(session.turns),
            "usage_breakdown": list(usage_by_model.values()),
            "totals": {
                "anthropic_input_tokens": total_anthropic_input,
                "anthropic_output_tokens": total_anthropic_output,
                "local_model_calls": total_local_calls,
                "estimated_cost_if_api_key": total_estimated_cost
            },
            "notes": [
                "All Anthropic API calls use SUBSCRIPTION CREDITS FIRST",
                "API key is only charged when subscription exhausted",
                "Actual cost may be $0 if using subscription credits",
                f"Estimated API key cost if no subscription: ${total_estimated_cost:.4f}",
                "Local LM Studio calls are always FREE"
            ]
        }
    
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
                "This is a CONSTRUCTIVE speech. You must GENERATE original arguments (do NOT extract from previous speeches):\n"
                "- CREATE NEW arguments supporting your position on this debate topic\n"
                "- Present evidence and reasoning to support your arguments\n"
                "- Build your case with 3-5 clear contentions\n"
                "- Cite sources with DESCRIPTIVE text: [Source: Harvard Medical School 2023 study] or [Source: USDA nutrition database]\n"
                "  NEVER use just numbers like [Source: 1] - always include the actual source name\n"
                "- Do NOT say 'I cannot' or provide meta-commentary about the task\n"
                "- Start immediately with your first argument (no preamble)\n"
            )

        elif speech_type == "cx_question":
            base += (
                "This is CROSS-EXAMINATION. You must GENERATE a question (do NOT extract from previous speeches):\n"
                "- CREATE ONE strategic question to challenge your opponent's most recent argument\n"
                "- Your question should expose weaknesses or contradictions in what they just said\n"
                "- Make your question clear, direct, and challenging\n"
                "- Do NOT answer the question - only ask it\n"
                "- Do NOT say 'I cannot' or provide meta-commentary\n"
                "- Start immediately with your question (no preamble)\n"
                "Example format: 'You claimed X, but how do you reconcile that with Y?'\n"
            )

        elif speech_type == "cx_answer":
            base += (
                "You are ANSWERING cross-examination. You must GENERATE an answer (do NOT extract from previous speeches):\n"
                "- CREATE a direct answer to the question that was just asked\n"
                "- Defend your position with brief reasoning\n"
                "- Clarify any misunderstandings or incorrect assumptions\n"
                "- Keep your answer focused and concise (2-3 sentences maximum)\n"
                "- Do NOT say 'I cannot' or provide meta-commentary\n"
                "- Start immediately with your answer (no preamble)\n"
            )

        elif speech_type == "rebuttal":
            base += (
                "This is a REBUTTAL speech. Deliver your rebuttal directly:\n"
                "- Refute your opponent's arguments\n"
                "- Extend your own arguments\n"
                "- Do NOT introduce brand new arguments\n"
                "- Focus on winning key issues in the debate\n"
                "- Cite sources with DESCRIPTIVE text: [Source: Harvard Medical School 2023 study] or [Source: USDA nutrition database]\n"
                "  NEVER use just numbers like [Source: 1] - always include the actual source name\n"
                "- Start immediately with your rebuttal\n"
            )

        elif speech_type == "closing":
            base += (
                "This is your CLOSING ARGUMENT. Deliver your final summary directly:\n"
                "- Summarize why your side should win this debate\n"
                "- Highlight your strongest arguments\n"
                "- Point out critical weaknesses in your opponent's case\n"
                "- Make your final persuasive appeal\n"
                "- Do NOT introduce new evidence or arguments\n"
                "- Keep it concise and powerful (2-3 paragraphs maximum)\n"
                "- Start immediately with your closing\n"
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

    def _format_with_haiku(self, raw_content: str, current_speech: dict) -> tuple[str, Optional[ModelUsage]]:
        """
        Format debate output using Claude Haiku (cheap, fast, effective).

        Uses subscription credits first, then API key.
        Cost: ~$0.001 per speech (60x cheaper than Opus).

        Returns:
            tuple of (formatted_content, usage_info)
        """
        # SKIP pre-cleaning - Haiku is smart enough to extract content from thinking blocks
        # The regex-based _strip_thinking_blocks() was too aggressive and removed actual content
        speech_type = current_speech["type"]

        # Build formatting instruction
        if speech_type == "constructive":
            instruction = (
                "Extract and polish the actual debate argument from this text. "
                "The text may contain thinking/reasoning blocks that you should IGNORE. "
                "Look for the actual debate speech content and format it as clear paragraphs. "
                "Keep all [Source: ...] citations intact. "
                "Output ONLY the formatted debate argument, nothing else."
            )
        elif speech_type == "cx_question":
            instruction = (
                "Extract the actual cross-examination question from this text. "
                "The text may contain thinking/reasoning blocks that you should IGNORE. "
                "Format the question as 1-2 direct, clear sentences. "
                "Output ONLY the formatted question, nothing else."
            )
        elif speech_type == "cx_answer":
            instruction = (
                "Extract the actual cross-examination answer from this text. "
                "The text may contain thinking/reasoning blocks that you should IGNORE. "
                "Format the answer as 1-2 clear, concise paragraphs. "
                "Output ONLY the formatted answer, nothing else."
            )
        elif speech_type == "rebuttal":
            instruction = (
                "Extract and polish the actual rebuttal from this text. "
                "The text may contain thinking/reasoning blocks that you should IGNORE. "
                "Look for the actual debate speech content and format it as clear paragraphs. "
                "Keep all [Source: ...] citations intact. "
                "Output ONLY the formatted rebuttal, nothing else."
            )
        elif speech_type == "closing":
            instruction = (
                "Extract and polish the actual closing argument from this text. "
                "The text may contain thinking/reasoning blocks that you should IGNORE. "
                "Format as clear, powerful paragraphs for maximum impact. "
                "Keep all [Source: ...] citations intact. "
                "Output ONLY the formatted closing argument, nothing else."
            )
        else:
            # Fallback for any other speech type
            instruction = (
                "Polish this content for readability. "
                "Format as clear paragraphs with proper structure."
            )

        # Call Haiku directly (uses subscription credits first automatically)
        try:
            from anthropic import Anthropic
            client = Anthropic()  # Uses ANTHROPIC_API_KEY from env

            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": f"{instruction}\n\nContent to format:\n\n{raw_content}"
                }]
            )

            # Extract text content
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            # Create usage record
            usage = ModelUsage(
                model="claude-haiku-4-5",
                model_type="anthropic",
                purpose="formatting",
                speech_name=current_speech["speech"],
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=0  # Not tracking latency for formatting
            )

            return content.strip(), usage

        except Exception as e:
            print(f"[Haiku] Formatting failed: {e}")
            print(f"[Haiku] Falling back to regex cleaning")
            # Fallback to regex if Haiku fails
            return self._strip_thinking_blocks(raw_content), None

    def _format_through_opus(self, raw_content: str, current_speech: dict) -> str:
        """
        Pass response through Claude Opus via DALS bridge for consistent formatting.

        Routes through bridge.py to use subscription credits first, then API key.
        This ensures all responses (from any model) are clean, professional,
        and properly formatted for debate display.
        """
        import hashlib
        from pathlib import Path

        # Bridge communication files
        bridge_base = Path("/Users/ssmithers/Desktop/CODE/dals")
        passon_file = bridge_base / "passon.md"
        response_file = bridge_base / "response.md"

        speech_type = current_speech["type"]

        # Determine cleaning requirements based on speech type
        if speech_type == "constructive":
            content_description = "constructive debate argument"
            expected_output = "3-5 paragraph argument with contentions"
        elif speech_type == "cx_question":
            content_description = "cross-examination question"
            expected_output = "1-2 direct questions"
        elif speech_type == "cx_answer":
            content_description = "cross-examination answer"
            expected_output = "1-2 paragraph response"
        else:  # rebuttal
            content_description = "rebuttal speech"
            expected_output = "2-4 paragraph rebuttal with refutations"

        # Build DALS task request for formatting
        request_message = (
            "## DALS Task: Clean LM Studio Output for AI Debate Simulator\n\n"
            f"**Project**: AI Debate Simulator (aidebate)\n"
            f"**Speech**: {current_speech['speech']} ({content_description})\n"
            f"**Source Model**: GLM-4.7-Flash via LM Studio\n\n"
            "**Task**: The text below is raw output from a local LLM that contains thinking blocks, "
            "numbered analysis sections, and meta-commentary. Please extract and format only the actual "
            f"debate content as a clean {expected_output}.\n\n"
            "**Cleaning Requirements**:\n"
            "- Remove all thinking blocks (e.g., '1. **Analyze:**', '<think>', numbered planning sections)\n"
            "- Remove meta-commentary about how arguments are constructed\n"
            "- Preserve [Source: ...] citations exactly as written\n"
            "- Format as clear, readable paragraphs\n"
            "- Return ONLY the cleaned debate content\n\n"
            f"**Expected Output Format**: {expected_output}\n\n"
            "---\n\n"
            f"**Raw LM Studio Output**:\n\n{raw_content}"
        )

        # Helper to get file hash
        def get_file_hash(path):
            if not path.exists():
                return ""
            return hashlib.md5(path.read_text().encode()).hexdigest()

        # Get current response.md hash before writing (to detect updates)
        old_response_hash = get_file_hash(response_file)

        # Write formatting request to passon.md
        passon_file.write_text(request_message)
        print(f"[Bridge] Formatting request sent for {current_speech['speech']}")

        # Wait for response.md to update (poll with timeout)
        timeout = 60  # seconds
        poll_interval = 2  # check every 2 seconds
        elapsed = 0

        while elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval

            current_hash = get_file_hash(response_file)
            if current_hash and current_hash != old_response_hash:
                # Response received from bridge!
                response_text = response_file.read_text()

                # Strip bridge header and metadata
                # Format: <!-- OPUS RESPONSE | timestamp -->
                #         *[Opus 4.6 | X in / Y out tokens]*
                #
                #         [actual content]
                lines = response_text.split('\n')
                content_lines = []

                for line in lines:
                    # Skip HTML comments and token usage lines
                    if line.strip().startswith('<!--') or line.strip().startswith('*[Opus'):
                        continue
                    content_lines.append(line)

                formatted_content = '\n'.join(content_lines).strip()
                print(f"[Bridge] Formatted response received from Opus (via subscription)")
                return formatted_content

        # Timeout - bridge might not be running
        print(f"[Bridge] ⚠️  WARNING: No response after {timeout}s")
        print(f"[Bridge] ⚠️  Is bridge.py running? Check: ps aux | grep bridge.py")
        print(f"[Bridge] ⚠️  Falling back to unformatted content")
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
