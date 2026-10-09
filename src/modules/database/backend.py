import logging
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
from modules.database.database import DATABASE, Database
from modules.database.models import MessageRow, SessionRow
from modules.memory.extractor import extract_and_store
from modules.server.server import Server

logger = logging.getLogger(__name__)

EXTRACTOR_NAME = "MEMORY_EXTRACTOR"


class SessionsBackend(Protocol):
    def list_sessions(self, agent_name: str) -> list[SessionRow]: ...
    def create_session(self, title: str, agent_name: str) -> SessionRow: ...
    def rename_session(self, title: str, session_id: int) -> None: ...
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
    async def extract_memories(
        self, agent_name: str, rows: Sequence[MessageRow]
    ) -> None: ...


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
        if EXTRACTOR_NAME not in basic:
            logger.warning(
                "Memory extractor '%s' not found: memories will be recalled but never created",
                EXTRACTOR_NAME,
            )

    def list_agents(self) -> list[AgentDefinition]:
        # Basic agents are exlcuded sinec they aren't used for chatting
        return [d for d in self._agent_definitions if d.type == "complete"]

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

    async def extract_memories(
        self, agent_name: str, rows: Sequence[MessageRow]
    ) -> None:
        extractor = self._basic_agents.get(EXTRACTOR_NAME)
        if extractor is None:
            return  # already warned at startup
        await extract_and_store(self._server, extractor, agent_name, rows)


class MockSessionBackend:
    _database: Database

    def __init__(self) -> None:
        # Share the module-level connection with the memory code instead of
        # opening a second one to the same file.
        self._database = DATABASE

    def list_sessions(self, agent_name: str) -> list[SessionRow]:
        return self._database.get_session_list(agent_name)

    def create_session(self, title: str, agent_name: str) -> SessionRow:
        return self._database.create_session(title, agent_name)

    def delete_session(self, session_id: int) -> None:
        self._database.delete_session(session_id)

    def get_messages(self, session_id: int) -> list[MessageRow]:
        return self._database.get_messages(session_id)

    def rename_session(self, title: str, session_id: int) -> None:
        self._database.rename_session(title, session_id)

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
