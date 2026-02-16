from pydantic import BaseModel, ConfigDict
from typing import Optional


class ModelUsage(BaseModel):
    """Track model usage for a single API call."""
    model_config = ConfigDict(protected_namespaces=())

    model: str  # e.g., "claude-opus-4-6", "glm-flash"
    model_type: str  # "anthropic" or "lm_studio"
    purpose: str  # "debate_content" or "formatting"
    speech_name: str  # e.g., "1AC", "CX by 2N"
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


class DebateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

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
    models: dict  # {aff: "glm-flash", neg: "quen3-coder"}
    speaker_positions: dict  # {model1: "2A/1N", model2: "2N/1A"}
    current_speech_index: int
    debate_flow: list[dict]  # List of speeches in order
    turns: list[DebateTurn]
    settings: dict
    status: str
    usage_log: list[ModelUsage] = []  # Track all model API calls
