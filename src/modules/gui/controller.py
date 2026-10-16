import asyncio
import logging
from pathlib import Path

from PyQt6.QtCore import (
    QObject,
    QUrl,
    pyqtProperty,  # pyright: ignore[reportAttributeAccessIssue]
    pyqtSignal,
    pyqtSlot,
)

from modules.agents.events import (
    GeneratingResponse,
    GenerationFinished,
    RunError,
    ToolCallFinished,
    ToolCallStarted,
)
from modules.agents.models import ImageSource, build_history
from modules.database.backend import AgentsBackend, SessionsBackend
from modules.gui.models import (
    AgentListModel,
    AttachmentItem,
    AttachmentListModel,
    MessageListModel,
    SessionListModel,
)

logger = logging.getLogger(__name__)

MAX_TOAST_CHARS = 300
EXTRACT_EVERY = 6
TITLE_PREFIX_MAX = 60


class AppController(QObject):
    selectedAgentChanged: pyqtSignal = pyqtSignal()
    selectedSessionChanged: pyqtSignal = pyqtSignal()
    generatingChanged: pyqtSignal = pyqtSignal()
    errorOccurred: pyqtSignal = pyqtSignal(str)
    restoreInput: pyqtSignal = pyqtSignal(str)
    agentCreated: pyqtSignal = pyqtSignal(str)

    _agent_backend: AgentsBackend
    _session_backend: SessionsBackend
    _selected_agent: str
    _selected_session_id: int
    _status: dict[int, str]
    _extracted_upto: dict[int, int]
    _bg_tasks: set[asyncio.Task[None]]

    _agent_list_model: AgentListModel
    _session_list_model: SessionListModel
    _message_list_model: MessageListModel
    _attachment_list_model: AttachmentListModel
    _tasks: dict[int, asyncio.Task[None]]
    _username: str
    _titled_sessions: set[int]

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
        self._attachment_list_model = AttachmentListModel()
        self._tasks = {}
        self._status = {}
        self._extracted_upto = {}
        self._bg_tasks = set()
        self._username = "toffeezzz"
        self._titled_sessions = set()
        self._agent_list_model.add(agent_backend.list_agents())

    # ---------- selection ----------
    @pyqtSlot(str)
    def selectAgent(self, name: str) -> None:
        if name != self._selected_agent:
            logger.info("New agent selected %s", name)
            self._selected_agent = name
            self._selected_session_id = -1
            self.selectedAgentChanged.emit()
            self.selectedSessionChanged.emit()
            self._message_list_model.reset_to([])
            sessions = self._session_backend.list_sessions(self._selected_agent)
            self._session_list_model.reset_to(sessions)

    @pyqtSlot(int, str)
    def selectSession(self, session_id: int, title: str) -> None:
        if session_id != self._selected_session_id:
            self._selected_session_id = session_id
            messages = self._session_backend.get_messages(session_id)
            logger.info("Session selected: %s", title)
            self.selectedSessionChanged.emit()
            self.generatingChanged.emit()
            self._message_list_model.reset_to(messages)

    # ---------- agent creation ----------
    @pyqtSlot(
        str, str, str, str, str,
        int,
        str, str, str, str, str,
        str, str, str,
        bool, result=bool
    )
    def createAgent(
        self,
        name: str,
        agent_type: str,
        language_model: str,
        persona: str,
        avatar_source: str,
        max_loop: int = 40,
        temperature: str = "",
        top_p: str = "",
        frequency_penalty: str = "",
        presence_penalty: str = "",
        reasoning_effort: str = "",
        max_completion_tokens: str = "",
        seed: str = "",
        stop: str = "",
        response_format: bool = False,
    ) -> bool:
        if avatar_source.startswith("file://"):
            avatar_source = QUrl(avatar_source).toLocalFile()

        if max_loop <= 0:
            max_loop = None

        def _float(value: str) -> float | None:
            if value == "":
                return None
            try:
                return float(value)
            except ValueError:
                return None

        def _int(value: str) -> int | None:
            if value == "":
                return None
            try:
                return int(value)
            except ValueError:
                return None

        try:
            self._agent_backend.create_agent(
                name=name,
                agent_type=agent_type,
                language_model=language_model,
                persona=persona,
                avatar_source=avatar_source,
                max_loop=max_loop,
                temperature=_float(temperature),
                top_p=_float(top_p),
                frequency_penalty=_float(frequency_penalty),
                presence_penalty=_float(presence_penalty),
                reasoning_effort=reasoning_effort or None,
                max_completion_tokens=_int(max_completion_tokens),
                seed=_int(seed),
                stop=([s.strip() for s in stop.split(",") if s.strip()] if stop else None),
                response_format={"type": "json_object"} if response_format else None,
            )
        except Exception as e:
            logger.exception("Failed to create agent")
            self.errorOccurred.emit(f"Failed to create agent: {e}")
            return False

        self._agent_list_model.reset_to(self._agent_backend.list_agents())
        logger.info("Agent created: %s", name)
        self.agentCreated.emit(name)
        self.selectAgent(name)
        return True

    @pyqtSlot(str, result=bool)
    def deleteAgent(self, name: str) -> bool:
        try:
            sessions = self._session_backend.list_sessions(name)
            for session in sessions:
                task = self._tasks.get(session.id)
                if task is not None and not task.done():
                    task.cancel()
            self._agent_backend.delete_agent(name)
            self._session_backend.delete_agent_data(name)
        except Exception as e:
            logger.exception("Failed to delete agent")
            self.errorOccurred.emit(f"Failed to delete agent: {e}")
            return False

        if name == self._selected_agent:
            self._selected_agent = ""
            self._selected_session_id = -1
            self.selectedAgentChanged.emit()
            self.selectedSessionChanged.emit()
            self._message_list_model.reset_to([])
            self._session_list_model.reset_to([])

        self._agent_list_model.reset_to(self._agent_backend.list_agents())
        logger.info("Agent deleted: %s", name)
        return True

    # ---------- sessions ----------
    @pyqtSlot()
    def createSession(self) -> None:
        if self._selected_agent == "":
            return
        row = self._session_backend.create_session(
            f"Session {self._session_list_model.rowCount()}", self._selected_agent
        )
        self._session_list_model.prepend(row)
        self.selectSession(row.id, row.title)

    @pyqtSlot()
    def deleteSession(self) -> None:
        self._session_backend.delete_session(self._selected_session_id)
        sessions = self._session_backend.list_sessions(self._selected_agent)
        self._session_list_model.reset_to(sessions)

    @pyqtSlot(str)
    def renameSession(self, title: str) -> None:
        session_id = self._selected_session_id
        self._session_list_model.rename(session_id, title)
        self._session_backend.rename_session(title, session_id)

    # ---------- messaging ----------
    @pyqtSlot(str)
    def addMessage(self, text: str) -> None:
        if text == "":
            return
        session_id = self._selected_session_id
        if session_id < 0:
            logger.warning("Message failed: No session selected/started")
            return
        if session_id in self._tasks:
            return

        attachments = self._attachment_list_model.take()
        pending_id = self._message_list_model.add_pending(
            session_id, self._username, text, attachments
        )

        task = asyncio.ensure_future(
            self._send(session_id, self._selected_agent, text, attachments, pending_id)
        )
        self._tasks[session_id] = task
        task.add_done_callback(lambda t, sid=session_id: self._on_task_done(sid, t))

    async def _send(
        self,
        session_id: int,
        agent_name: str,
        text: str,
        attachments: list[AttachmentItem],
        pending_id: int,
    ) -> None:
        username = self._username
        user_saved = False
        failed = False
        self._set_status(session_id, "Thinking\u2026")

        try:
            message_rows = self._session_backend.get_messages(session_id)
            history = await asyncio.to_thread(build_history, message_rows)
            images: list[ImageSource] = [
                Path(a.path) for a in attachments if a.is_image
            ]

            async for event in self._agent_backend.run_complete_agent(
                agent_name, username, text, history=history, images=images
            ):
                match event:
                    case GeneratingResponse():
                        self._set_status(session_id, "Thinking\u2026")
                    case GenerationFinished(content=c):
                        self._set_status(session_id, None)
                        if not user_saved:
                            saved = self._session_backend.add_message(
                                session_id,
                                "user",
                                text,
                                username,
                                attachments=[a.path for a in attachments],
                            )
                            self._message_list_model.confirm_pending(pending_id, saved)
                            user_saved = True
                            self._maybe_title_session(session_id, text)
                        if c.strip():
                            reply = self._session_backend.add_message(
                                session_id, "assistant", c, agent_name
                            )
                            if self._selected_session_id == session_id:
                                self._message_list_model.append(reply)
                    case ToolCallStarted(name=n):
                        self._set_status(session_id, f"Running {n}\u2026")
                    case ToolCallFinished():
                        self._set_status(session_id, "Thinking\u2026")
                    case RunError(message=m):
                        failed = True
                        logger.warning("Run failed, user message not saved: %s", m)
                        self._fail(m, session_id, attachments)

            if not failed:
                self._schedule_extraction(session_id, agent_name)
        except asyncio.CancelledError:
            if not user_saved:
                if self._selected_session_id == session_id:
                    self._message_list_model.remove_by_id(pending_id)
                self._fail("Generation stopped", session_id, attachments, text)
            raise
        except Exception as e:
            logger.exception("Unexpected error while sending")
            self._fail(f"{type(e).__name__}: {e}", session_id, attachments)
        finally:
            self._set_status(session_id, None)

    def _maybe_title_session(self, session_id: int, text: str) -> None:
        if session_id in self._titled_sessions:
            return
        self._titled_sessions.add(session_id)
        task = asyncio.ensure_future(self._generate_title(session_id, text))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _generate_title(self, session_id: int, text: str) -> None:
        try:
            current = self._session_backend.get_session(session_id)
            if current is None or not current.title.startswith("Session "):
                return
            fallback = self._humanize_title(text)
            title = await self._agent_backend.generate_title(text)
            new_title = title or fallback
            self._session_backend.rename_session(new_title, session_id)
            self._session_list_model.rename(session_id, new_title)
        except Exception:
            logger.exception("Failed to title session: %s", session_id)

    @staticmethod
    def _humanize_title(text: str) -> str:
        clean = " ".join(text.split())
        if len(clean) > TITLE_PREFIX_MAX:
            clean = clean[:TITLE_PREFIX_MAX].rstrip()
        return clean

    def _schedule_extraction(self, session_id: int, agent_name: str) -> None:
        rows = self._session_backend.get_messages(session_id)
        last = self._extracted_upto.get(session_id, 0)
        fresh = [r for r in rows if r.id > last]
        if len(fresh) < EXTRACT_EVERY:
            return
        fresh = fresh[-20:]
        self._extracted_upto[session_id] = fresh[-1].id

        task = asyncio.ensure_future(
            self._agent_backend.extract_memories(agent_name, fresh)
        )
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    def _fail(
        self,
        message: str,
        session_id: int,
        attachments: list[AttachmentItem],
        restore_text: str = "",
    ) -> None:
        self.errorOccurred.emit(message[:MAX_TOAST_CHARS])
        if self._selected_session_id == session_id:
            self._attachment_list_model.restore(attachments)
            if restore_text:
                self.restoreInput.emit(restore_text)

    def _on_task_done(self, session_id: int, task: asyncio.Task[None]) -> None:
        if self._tasks.get(session_id) is task:
            del self._tasks[session_id]
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("Send failed", exc_info=exc)

    def _set_status(self, session_id: int, label: str | None) -> None:
        if label is None:
            if self._status.pop(session_id, None) is None:
                return
        else:
            if self._status.get(session_id) == label:
                return
            self._status[session_id] = label
        if session_id == self._selected_session_id:
            self.generatingChanged.emit()

    @pyqtSlot()
    def stopGeneration(self) -> None:
        task = self._tasks.get(self._selected_session_id)
        if task is not None and not task.done():
            _ = task.cancel()

    # ---------- properties exposed to QML ----------
    @pyqtProperty(bool, notify=generatingChanged)
    def isGenerating(self) -> bool:
        return self._selected_session_id in self._status

    @pyqtProperty(str, notify=generatingChanged)
    def thinkingLabel(self) -> str:
        return self._status.get(self._selected_session_id, "")

    @pyqtProperty(str, constant=True)
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

    @pyqtProperty(QObject, constant=True)
    def attachmentModel(self) -> QObject:
        return self._attachment_list_model