from typing import Any, override

from PyQt6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt, QUrl

from modules.database.models import MessageRow, SessionRow


class AgentListModel(QAbstractListModel):
    NameRole: int = Qt.ItemDataRole.UserRole + 1
    ImagePathRole: int = Qt.ItemDataRole.UserRole + 2

    def __init__(self) -> None:
        super().__init__()
        self._agents: list[dict[str, str]] = []

    @override
    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.NameRole: QByteArray(b"agentName"),
            self.ImagePathRole: QByteArray(b"imagePath"),
        }

    @override
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._agents)

    @override
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._agents):
            return None
        row = self._agents[index.row()]
        if role == self.NameRole:
            return row["agentName"]
        if role == self.ImagePathRole:
            return QUrl.fromLocalFile(row["imagePath"]).toString()
        return None

    def add(self, agent_name: str, image_path: str) -> None:
        pos = len(self._agents)
        self.beginInsertRows(QModelIndex(), pos, pos)
        self._agents.append({"agentName": agent_name, "imagePath": image_path})
        self.endInsertRows()


class SessionListModel(QAbstractListModel):
    TitleRole: int = Qt.ItemDataRole.UserRole + 1
    IdRole: int = Qt.ItemDataRole.UserRole + 2
    AgentRole: int = Qt.ItemDataRole.UserRole + 3

    def __init__(self) -> None:
        super().__init__()
        self._sessions: list[SessionRow] = []

    @override
    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.TitleRole: QByteArray(b"title"),
            self.IdRole: QByteArray(b"sessionId"),
            self.AgentRole: QByteArray(b"agentName"),
        }

    @override
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._sessions)

    @override
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._sessions):
            return None
        s = self._sessions[index.row()]
        if role == self.TitleRole:
            return s.title
        if role == self.IdRole:
            return s.id
        if role == self.AgentRole:
            return s.agent_name
        return None

    def reset_to(self, sessions: list[SessionRow]) -> None:
        self.beginResetModel()
        self._sessions = list(sessions)
        self.endResetModel()

    def prepend(self, session: SessionRow) -> None:
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._sessions.insert(0, session)
        self.endInsertRows()

    def remove_by_id(self, session_id: int) -> None:
        for i, s in enumerate(self._sessions):
            if s.id == session_id:
                self.beginRemoveRows(QModelIndex(), i, i)
                del self._sessions[i]
                self.endRemoveRows()
                return

    def rename(self, session_id: int, title: str) -> None:
        for i, s in enumerate(self._sessions):
            if s.id == session_id:
                self._sessions[i] = s.model_copy(
                    update={"title": title}
                )  # frozen, so replace it
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [self.TitleRole])
                return


class MessageListModel(QAbstractListModel):
    TextRole: int = Qt.ItemDataRole.UserRole + 1
    IdRole: int = Qt.ItemDataRole.UserRole + 2
    RoleRole: int = Qt.ItemDataRole.UserRole + 3

    def __init__(self) -> None:
        super().__init__()
        self._sessions: list[MessageRow] = []

    @override
    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.TextRole: QByteArray(b"text"),
            self.IdRole: QByteArray(b"messageId"),
            self.RoleRole: QByteArray(b"role"),
        }

    @override
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._sessions)

    @override
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._sessions):
            return None
        s = self._sessions[index.row()]
        if role == self.TextRole:
            return s.text
        if role == self.IdRole:
            return s.id
        if role == self.RoleRole:
            return s.role
        return None

    def reset_to(self, messages: list[MessageRow]) -> None:
        self.beginResetModel()
        self._sessions = list(messages)
        self.endResetModel()

    def prepend(self, message: MessageRow) -> None:
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._sessions.insert(0, message)
        self.endInsertRows()

    def remove_by_id(self, message_id: int) -> None:
        for i, s in enumerate(self._sessions):
            if s.id == message_id:
                self.beginRemoveRows(QModelIndex(), i, i)
                del self._sessions[i]
                self.endRemoveRows()
                return

    def edit_by_id(self, message_id: int, text: str) -> None:
        for i, s in enumerate(self._sessions):
            if s.id == message_id:
                self._sessions[i] = s.model_copy(update={"text": text})
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [self.TextRole])
                return
