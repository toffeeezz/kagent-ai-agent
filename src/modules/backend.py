from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolChoiceOptionParam,
)

from modules.agents.builder import scan_agent_dir
from modules.agents.errors import AgentError
from modules.agents.events import AgentEvent
from modules.agents.models import (
    AgentDefinition,
    BasicAgent,
    CompleteAgent,
    ImageSource,
)
from modules.database.database import Database
from modules.database.models import MessageRow, SessionRow
from modules.server.server import Server


class SessionsBackend(Protocol):
    def list_sessions(self, agent_name: str) -> list[SessionRow]: ...
    def create_session(self, title: str, agent_name: str) -> SessionRow: ...
    def delete_session(self, session_id: int) -> None: ...
    def get_messages(self, session_id: int) -> list[MessageRow]: ...
    def add_message(
        self,
        session_id: int,
        role: str,
        text: str,
        speaker_name: str,
        attachments: Sequence[str] = (),
    ) -> MessageRow: ...


class AgentsBackend(Protocol):
    def list_agents(self) -> list[AgentDefinition]: ...
    def run_complete_agent(
        self,
        agent_name: str,
        username: str,
        input: str,
        images: Sequence[ImageSource] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        history: list[ChatCompletionMessageParam] | None = None,
    ) -> AsyncIterator[AgentEvent]: ...


class MockAgentsBackend:
    _server: Server
    _complete_agents: dict[str, CompleteAgent]
    _basic_agents: dict[str, BasicAgent]
    _agent_definitions: list[AgentDefinition]

    def __init__(self, server: Server) -> None:
        basic, complete, definitions = scan_agent_dir()
        self._complete_agents = complete
        self._basic_agents = basic
        self._agent_definitions = definitions
        self._server = server

    def list_agents(self) -> list[AgentDefinition]:
        return self._agent_definitions

    async def run_complete_agent(
        self,
        agent_name: str,
        username: str,
        input: str,
        images: Sequence[ImageSource] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        history: list[ChatCompletionMessageParam] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        agent = self._complete_agents.get(agent_name)
        if agent is None:
            raise AgentError(
                f"Complete agent named {agent_name} could not be found", agent_name
            )
        async for event in agent.run(
            self._server, username, input, images, tool_choice, history
        ):
            yield event


class MockSessionBackend:
    _database: Database

    def __init__(self) -> None:
        self._database = Database()

    def list_sessions(self, agent_name: str) -> list[SessionRow]:
        return self._database.get_session_list(agent_name)

    def create_session(self, title: str, agent_name: str) -> SessionRow:
        return self._database.create_session(title, agent_name)

    def delete_session(self, session_id: int) -> None:
        self._database.delete_session(session_id)

    def get_messages(self, session_id: int) -> list[MessageRow]:
        return self._database.get_messages(session_id)

    def add_message(
        self,
        session_id: int,
        role: str,
        text: str,
        speaker_name: str,
        attachments: Sequence[str] = (),
    ) -> MessageRow:
        return self._database.add_message(
            session_id, role, text, speaker_name, attachments
        )
