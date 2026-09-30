from pydantic import BaseModel


class SessionRow(BaseModel):
    id: int
    title: str
    created_at: str


class MessageRow(BaseModel):
    id: int
    session_id: int
    role: str
    text: str
    created_at: str


class MemoryRow(BaseModel):
    id: int
    agent_name: str
    text: str
    importance: float
    retrieval_score: float
    last_accessed: str
    created_at: str
