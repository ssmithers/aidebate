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
    
    def start_debate(self, topic: str, model1: str, model2: str, pro_model: str) -> DebateSession:
        """
        Create a new debate session.
        
        Args:
            topic: The debate topic
            model1: First model alias
            model2: Second model alias
            pro_model: Which model takes the "pro" stance ("model1" or "model2")
        
        Returns:
            DebateSession object
        """
        session_id = str(uuid.uuid4())
        
        # Assign pro/con roles
        if pro_model == "model1":
            models = {"pro": model1, "con": model2}
        else:
            models = {"pro": model2, "con": model1}
        
        session = DebateSession(
            session_id=session_id,
            topic=topic,
            models=models,
            turns=[],
            settings={"temperature": 0.3, "max_tokens": 16384},
            status="active"
        )
        
        self._save_session(session)
        return session
    
    def execute_turn(self, session_id: str, moderator_message: str | None = None) -> DebateTurn:
        """
        Execute one debate turn (both models respond).
        
        CRITICAL: Calls LM Studio sequentially (not parallel) per CLAUDE.md requirement.
        
        Args:
            session_id: Session UUID
            moderator_message: Optional moderator question/direction
        
        Returns:
            DebateTurn with both responses
        """
        session = self._load_session(session_id)
        
        turn_id = len(session.turns) + 1
        
        # Build contexts for both stances
        context_pro = self._build_context(session, "pro", moderator_message)
        context_con = self._build_context(session, "con", moderator_message)
        
        # SEQUENTIAL calls to LM Studio (CRITICAL - cannot be parallel)
        result_pro = self.worker.chat(
            session.models["pro"],
            context_pro,
            temperature=session.settings["temperature"],
            max_tokens=session.settings["max_tokens"]
        )
        
        result_con = self.worker.chat(
            session.models["con"],
            context_con,
            temperature=session.settings["temperature"],
            max_tokens=session.settings["max_tokens"]
        )
        
        # Process citations (strip thinking blocks first)
        if result_pro["success"]:
            clean_content = self._strip_thinking_blocks(result_pro["content"])
            content_pro, citations_pro = extract_citations(clean_content)
        else:
            content_pro = f"[ERROR: {result_pro['error']}]"
            citations_pro = []

        if result_con["success"]:
            clean_content = self._strip_thinking_blocks(result_con["content"])
            content_con, citations_con = extract_citations(clean_content)
        else:
            content_con = f"[ERROR: {result_con['error']}]"
            citations_con = []
        
        # Create turn
        turn = DebateTurn(
            turn_id=turn_id,
            moderator_message=moderator_message,
            responses=[
                DebateResponse(
                    model_alias=session.models["pro"],
                    stance="pro",
                    content=content_pro,
                    citations=citations_pro,
                    latency_ms=result_pro["latency_ms"]
                ),
                DebateResponse(
                    model_alias=session.models["con"],
                    stance="con",
                    content=content_con,
                    citations=citations_con,
                    latency_ms=result_con["latency_ms"]
                )
            ],
            timestamp=time.time()
        )
        
        # Update session
        session.turns.append(turn)
        self._save_session(session)
        
        return turn
    
    def end_topic(self, session_id: str) -> DebateSession:
        """Mark session as completed."""
        session = self._load_session(session_id)
        session.status = "completed"
        self._save_session(session)
        return session
    
    def _build_context(self, session: DebateSession, stance: str, moderator_message: str | None) -> list[dict]:
        """
        Build message context for a model.
        
        System prompt enforces stance, then all previous turns in conversation format.
        Same stance = assistant (my previous words), opposite = user (opponent).
        """
        system_prompt = self._get_system_prompt(session.topic, stance, moderator_message)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add all previous turns
        for turn in session.turns:
            # Moderator message appears as user message to both
            if turn.moderator_message:
                messages.append({"role": "user", "content": f"[Moderator]: {turn.moderator_message}"})
            
            # Add responses (same stance = assistant, opposite = user)
            for response in turn.responses:
                if response.stance == stance:
                    messages.append({"role": "assistant", "content": response.content})
                else:
                    messages.append({"role": "user", "content": response.content})
        
        return messages
    
    def _get_system_prompt(self, topic: str, stance: str, moderator_message: str | None) -> str:
        """Generate system prompt enforcing stance and format."""
        base = (
            f"You are participating in a civil debate on the topic: '{topic}'.\n\n"
            f"You MUST argue the {stance.upper()} position on this topic.\n\n"
            "Rules:\n"
            "- Keep responses concise (2-4 sentences)\n"
            "- Cite sources when making factual claims using [Source: ...] format\n"
            "- Be respectful and focus on logic and evidence\n"
            "- Address your opponent's points directly\n"
        )
        
        if moderator_message:
            base += f"\n\nThe moderator has asked: {moderator_message}\n"
            base += "Address this question in your response.\n"
        
        return base
    
    def _strip_thinking_blocks(self, text: str) -> str:
        """
        Remove thinking blocks from model output.

        Some models (GLM-4.7-Flash, DeepSeek R1) leak thinking content before </think> tag.
        Strip everything up to and including </think> tag.
        """
        import re
        # Pattern 1: Remove <think>...</think> blocks (full tags)
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Pattern 2: Remove everything before and including </think> (leaked blocks without opening tag)
        cleaned = re.sub(r'^.*?</think>\s*', '', cleaned, flags=re.DOTALL)
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
