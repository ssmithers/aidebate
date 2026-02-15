from pydantic import BaseModel
from typing import Optional


class DebateResponse(BaseModel):
    model_alias: str
    stance: str  # "pro" or "con"
    content: str
    citations: list[dict]
    latency_ms: int


class DebateTurn(BaseModel):
    turn_id: int
    moderator_message: Optional[str] = None
    responses: list[DebateResponse]
    timestamp: float


class DebateSession(BaseModel):
    session_id: str
    topic: str
    models: dict  # {pro: "glm-flash", con: "qwen3-coder"}
    turns: list[DebateTurn]
    settings: dict
    status: str
