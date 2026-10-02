import logging

from PyQt6.QtCore import (
    QObject,
    pyqtProperty,  # pyright: ignore[reportAttributeAccessIssue]
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtWidgets import QFileDialog

from modules.backend import AgentsBackend, SessionsBackend
from modules.gui.models import AgentListModel, MessageListModel, SessionListModel

logger = logging.getLogger(__name__)


class AppController(QObject):
    selectedAgentChanged: pyqtSignal = pyqtSignal()
    selectedSessionChanged: pyqtSignal = pyqtSignal()

    _agent_backend: AgentsBackend
    _session_backend: SessionsBackend
    _selected_agent: str
    _selected_session_id: int

    _agent_list_model: AgentListModel
    _session_list_model: SessionListModel
    _message_list_model: MessageListModel
    _dialog: QFileDialog

    def __init__(
        self,
        agent_backend: AgentsBackend,
        session_backend: SessionsBackend,
        parent: QObject | None = None,
    ) -> None:
        super().__init__()
        self._agent_backend = agent_backend
        self._session_backend = session_backend
        self._selected_agent = ""
        self._selected_session_id = -1
        self._agent_list_model = AgentListModel()
        self._session_list_model = SessionListModel()
        self._message_list_model = MessageListModel()
        self._dialog = QFileDialog()
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
        dialog = QFileDialog()
        dialog.setWindowTitle("Attach files")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.webp);;All files (*)")
        self._dialog = dialog  # keep a reference, or it's garbage collected right away
        dialog.open()

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
