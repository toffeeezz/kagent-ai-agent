import asyncio
import datetime
import logging

from openai.types.chat import ChatCompletionMessageParam
from PyQt6.QtCore import (
    QObject,
    pyqtProperty,  # pyright: ignore[reportAttributeAccessIssue]
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtWidgets import QFileDialog

from modules.agents.events import (
    GeneratingResponse,
    GenerationFinished,
    RunError,
    ToolCallFinished,
    ToolCallStarted,
)
from modules.backend import (
    AgentsBackend,
    MessageRow,
    SessionsBackend,
)
from modules.gui.models import AgentListModel, MessageListModel, SessionListModel

logger = logging.getLogger(__name__)

PENDING_MESSAGE_ID = -1


class AppController(QObject):
    selectedAgentChanged: pyqtSignal = pyqtSignal()
    selectedSessionChanged: pyqtSignal = pyqtSignal()
    usernameChanged: pyqtSignal = pyqtSignal()

    _agent_backend: AgentsBackend
    _session_backend: SessionsBackend
    _selected_agent: str
    _selected_session_id: int

    _agent_list_model: AgentListModel
    _session_list_model: SessionListModel
    _message_list_model: MessageListModel
    _dialog: QFileDialog
    _tasks: set[asyncio.Task[None]]
    _username: str

    def __init__(
        self,
        agent_backend: AgentsBackend,
        session_backend: SessionsBackend,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._agent_backend = agent_backend
        self._session_backend = session_backend
        self._selected_agent = ""
        self._selected_session_id = -1
        self._agent_list_model = AgentListModel()
        self._session_list_model = SessionListModel()
        self._message_list_model = MessageListModel()
        self._dialog = QFileDialog()
        self._tasks = set()
        self._username = "John"
        for agent in agent_backend.list_agents():
            if agent.type == "basic":
                continue
            self._agent_list_model.add(agent.name, agent.image_path)

    @pyqtSlot(str)
    def selectAgent(self, name: str) -> None:
        if name != self._selected_agent:
            logger.info("New agent selected %s", name)
            self._selected_agent = name
            self.selectedAgentChanged.emit()
            sessions = self._session_backend.list_sessions(self._selected_agent)
            self._session_list_model.reset_to(sessions)

    @pyqtSlot(int, str)
    def selectSession(self, session_id: int, title: str) -> None:
        if session_id != self._selected_session_id:
            self._selected_session_id = session_id
            messages = self._session_backend.get_messages(session_id)
            logger.info("Session selected: %s", title)
            self.selectedSessionChanged.emit()
            self._message_list_model.reset_to(messages)

    @pyqtSlot()
    def pickFiles(self) -> None:
        print("opening files")
        dialog = QFileDialog()
        dialog.setWindowTitle("Attach files")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.webp);;All files (*)")
        self._dialog = dialog
        dialog.open()

    @pyqtSlot()
    def createSession(self) -> None:
        session_list_count = self._session_list_model.rowCount()
        agent = self._selected_agent
        if self._selected_agent == "":
            return
        row = self._session_backend.create_session(
            f"Session {session_list_count}", agent
        )
        self._session_list_model.prepend(row)
        self.selectSession(row.id, row.title)

    @pyqtSlot()
    def deleteSession(self) -> None:
        sesson_id = self._selected_session_id
        self._session_backend.delete_session(sesson_id)
        sessions = self._session_backend.list_sessions(self._selected_agent)
        self._session_list_model.reset_to(sessions)

    @pyqtSlot(str)
    def addMessage(self, text: str) -> None:
        if self._selected_session_id < 0:
            logger.warning("Message failed: No session selected/started")
            return

        pending = MessageRow(
            id=PENDING_MESSAGE_ID,
            session_id=self._selected_session_id,
            role="user",
            speaker_name=self._username,
            text=text,
            created_at=datetime.datetime.now(datetime.UTC).isoformat(
                sep=" ", timespec="seconds"
            ),
        )
        self._message_list_model.append(pending)

        task = asyncio.ensure_future(self._send(text))
        self._tasks.add(task)  # keeping a reference so it isn't garbage collected
        task.add_done_callback(self._on_task_done)

    async def _send(self, text: str) -> None:
        session_id = self._selected_session_id
        agent_name = self._selected_agent
        username = self._username

        message_rows = self._session_backend.get_messages(session_id)
        messages: list[ChatCompletionMessageParam] = [
            {"role": "user", "content": f"[User {row.speaker_name}]: {row.text}"}
            if row.role == "user"
            else {"role": "assistant", "content": row.text}
            for row in message_rows
        ]

        user_saved = False

        async for event in self._agent_backend.run_complete_agent(
            agent_name, username, text, history=messages
        ):
            match event:
                case GeneratingResponse():
                    print("thinking")
                case GenerationFinished(content=c) if c.strip():
                    if not user_saved:
                        _ = self._session_backend.add_message(
                            session_id, "user", text, username
                        )
                        user_saved = True

                    message_row = self._session_backend.add_message(
                        session_id, "assistant", c, agent_name
                    )
                    if self._selected_session_id == session_id:
                        self._message_list_model.append(message_row)
                case ToolCallStarted(name=n):
                    ...
                case ToolCallFinished(ok=ok, summary=s):
                    ...
                case RunError(message=m):
                    logger.warning("Run failed, user message not saved: %s", m)
                case _:
                    logger.warning("Event returned an unhandled case %s", type(event))

    def _on_task_done(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("Send failed", exc_info=exc)

    @pyqtProperty(str, notify=usernameChanged)
    def username(self) -> str:
        return self._username

    @pyqtProperty(str, notify=selectedAgentChanged)
    def selectedAgent(self) -> str:
        return self._selected_agent

    @pyqtProperty(int, notify=selectedSessionChanged)
    def selectedSessionId(self) -> int:
        return self._selected_session_id

    @pyqtProperty(QObject, constant=True)
    def agentModel(self) -> QObject:
        return self._agent_list_model

    @pyqtProperty(QObject, constant=True)
    def sessionModel(self) -> QObject:
        return self._session_list_model

    @pyqtProperty(QObject, constant=True)
    def messageModel(self) -> QObject:
        return self._message_list_model
