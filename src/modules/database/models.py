from pydantic import BaseModel, ConfigDict


class SessionRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    title: str
    agent_name: str
    created_at: str


class MessageRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    session_id: int
    role: str
    text: str
    created_at: str
    speaker_name: str
    attachments: tuple[str, ...] = ()


class MemoryRow(BaseModel):
    id: int
    agent_name: str
    content: str
    recall_score: float
    importance: float
    created_at: str
    last_accessed_at: str
    message_ids: tuple[int, ...] = ()
    # only set by search_memories / recall_memories
    distance: float | None = None
    similarity: float | None = None
    score: float | None = None  # only set by recall_memories
