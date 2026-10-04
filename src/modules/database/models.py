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
    model_config = ConfigDict(frozen=True)
    id: int
    agent_name: str
    text: str
    importance: float
    retrieval_score: float
    last_accessed: str
    created_at: str
