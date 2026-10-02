from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Protocol, final

from modules.agents.builder import scan_agent_dir
from modules.agents.events import AgentEvent
from modules.agents.models import AgentDefinition, BaseAgent
from modules.database.models import MessageRow, SessionRow


class SessionsBackend(Protocol):
    def list_sessions(self, agent_name: str) -> list[SessionRow]: ...
    def create_session(self, title: str, agent_name: str) -> SessionRow: ...
    def delete_session(self, session_id: int) -> None: ...
    def rename(self, session_id: int, title: str) -> None: ...
    def get_messages(self, session_id: int) -> list[MessageRow]: ...
    def add_message(self, session_id: int, role: str, text: str) -> MessageRow: ...


class AgentsBackend(Protocol):
    def list_agents(self) -> list[AgentDefinition]: ...


class MockAgentsBackend:
    def list_agents(self) -> list[AgentDefinition]:
        basic, complete, definitions = scan_agent_dir()

        return definitions


# agent -> list of (session title, [(role, text), ...])
SEED: dict[str, list[tuple[str, list[tuple[str, str]]]]] = {
    "Ame": [
        (
            "Planning the QML layout",
            [
                (
                    "user",
                    "I want a left panel with my agents and a chat area on the right.",
                ),
                (
                    "assistant",
                    "Use a RowLayout: a fixed-width left panel and a chat area with Layout.fillWidth.",
                ),
                ("user", "How do I stop long agent names from stretching the panel?"),
                (
                    "assistant",
                    "Set elide on the Text and give it Layout.fillWidth so the layout bounds its width.",
                ),
                ("user", "That worked, thanks."),
            ],
        ),
        (
            "Debugging the list model",
            [
                ("user", "My ListView shows nothing even though I called add()."),
                (
                    "assistant",
                    "Check that the role names in roleNames() match the delegate's required properties.",
                ),
                ("user", "They were different. I had name instead of agentName."),
                (
                    "assistant",
                    "That's the usual cause. The delegate silently gets nothing when the names differ.",
                ),
            ],
        ),
    ],
    "Amadeus": [
        (
            "Memory design notes",
            [
                ("user", "Should memories be stored per agent or shared?"),
                (
                    "assistant",
                    "Per agent is simpler: each memory row carries an agent_name and searches filter on it.",
                ),
                ("user", "And core memories?"),
                (
                    "assistant",
                    "Keep a separate table of promoted memory ids, so promoting and demoting never touches the memory itself.",
                ),
            ],
        ),
        (
            "Weekend reading list",
            [
                ("user", "Can you suggest something to read this weekend?"),
                ("assistant", "Do you prefer fiction or technical books?"),
                ("user", "Technical, something about databases."),
                (
                    "assistant",
                    "Designing Data-Intensive Applications is a solid pick. It covers storage engines, replication and more.",
                ),
                ("user", "Perfect, I'll start with the storage chapter."),
            ],
        ),
    ],
}


@final
class MockSessionStore:
    """In-memory SessionStore with seeded data. Nothing is persisted."""

    def __init__(self) -> None:
        self._sessions: dict[int, SessionRow] = {}
        self._messages: dict[int, list[MessageRow]] = {}
        self._next_session_id = 1
        self._next_message_id = 1
        self._clock = datetime(2026, 9, 28, 9, 0, 0)
        self._seed()

    # ---------- SessionStore ----------
    def list_sessions(self, agent_name: str) -> list[SessionRow]:
        rows = [s for s in self._sessions.values() if s.agent_name == agent_name]
        return sorted(rows, key=lambda s: (s.created_at, s.id), reverse=True)

    def create_session(self, title: str, agent_name: str) -> SessionRow:
        row = SessionRow(
            id=self._next_session_id,
            title=title,
            agent_name=agent_name,
            created_at=self._now(),
        )
        self._next_session_id += 1
        self._sessions[row.id] = row
        self._messages[row.id] = []
        return row

    def delete_session(self, session_id: int) -> None:
        if session_id not in self._sessions:
            raise KeyError(f"No session found with id {session_id}")
        del self._sessions[session_id]
        del self._messages[session_id]

    def rename(self, session_id: int, title: str) -> None:
        row = self._sessions.get(session_id)
        if row is None:
            raise KeyError(f"No session found with id {session_id}")
        self._sessions[session_id] = row.model_copy(update={"title": title})

    def get_messages(self, session_id: int) -> list[MessageRow]:
        if session_id not in self._sessions:
            raise KeyError(f"No session found with id {session_id}")
        return list(self._messages[session_id])

    # ---------- extras for the mock (not in the protocol) ----------
    def add_message(self, session_id: int, role: str, text: str) -> MessageRow:
        if session_id not in self._sessions:
            raise KeyError(f"No session found with id {session_id}")
        row = MessageRow(
            id=self._next_message_id,
            session_id=session_id,
            role=role,
            text=text,
            created_at=self._now(),
        )
        self._next_message_id += 1
        self._messages[session_id].append(row)
        return row

    # ---------- internals ----------
    def _now(self) -> str:
        """Fake clock that moves forward one minute per call, so ordering is stable."""
        self._clock += timedelta(minutes=1)
        return self._clock.isoformat(sep=" ", timespec="seconds")

    def _seed(self) -> None:
        for agent_name, sessions in SEED.items():
            for title, messages in sessions:
                session = self.create_session(title, agent_name)
                for role, text in messages:
                    _ = self.add_message(session.id, role, text)
