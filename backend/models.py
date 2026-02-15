from pydantic import BaseModel
from typing import Optional


class DebateResponse(BaseModel):
    model_alias: str
    stance: str  # "aff" or "neg"
    speaker_position: str  # "1A", "2A", "1N", "2N"
    content: str
    citations: list[dict]
    latency_ms: int


class DebateTurn(BaseModel):
    turn_id: int
    speech_type: str  # "constructive", "cx_question", "cx_answer", "rebuttal"
    speech_name: str  # "1AC", "CX by 2N", "1NC", etc.
    speaker_position: str  # "1A", "2N", etc.
    moderator_message: Optional[str] = None
    responses: list[DebateResponse]
    timestamp: float


class DebateSession(BaseModel):
    session_id: str
    topic: str
    debate_format: str  # "policy" for policy debate structure
    models: dict  # {aff: "glm-flash", neg: "qwen3-coder"}
    speaker_positions: dict  # {model1: "2A/1N", model2: "2N/1A"}
    current_speech_index: int
    debate_flow: list[dict]  # List of speeches in order
    turns: list[DebateTurn]
    settings: dict
    status: str
