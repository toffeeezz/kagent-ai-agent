from dataclasses import dataclass
from mimetypes import guess_type
from pathlib import Path
from typing import Any, override

from PyQt6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    Qt,
    QUrl,
    pyqtProperty,  # pyright: ignore[reportAttributeAccessIssue]
    pyqtSignal,
    pyqtSlot,
)

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
    AttachmentsRole: int = Qt.ItemDataRole.UserRole + 4

    def __init__(self) -> None:
        super().__init__()
        self._messages: list[MessageRow] = []

    @override
    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.TextRole: QByteArray(b"text"),
            self.IdRole: QByteArray(b"messageId"),
            self.RoleRole: QByteArray(b"role"),
            self.AttachmentsRole: QByteArray(b"attachments"),
        }

    @override
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._messages)

    @override
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._messages):
            return None
        s = self._messages[index.row()]
        if role == self.TextRole:
            return s.text
        if role == self.IdRole:
            return s.id
        if role == self.RoleRole:
            return s.role
        if role == self.AttachmentsRole:
            items = (AttachmentItem.from_path(p) for p in s.attachments)
            return [
                {"name": i.name, "url": i.url, "isImage": i.is_image, "path": i.path}
                for i in items
            ]
        return None

    def reset_to(self, messages: list[MessageRow]) -> None:
        self.beginResetModel()
        self._messages = list(messages)
        self.endResetModel()

    def append(self, message: MessageRow) -> None:
        self.beginInsertRows(QModelIndex(), len(self._messages), len(self._messages))
        self._messages.append(message)
        self.endInsertRows()

    def remove_by_id(self, message_id: int) -> None:
        for i, s in enumerate(self._messages):
            if s.id == message_id:
                self.beginRemoveRows(QModelIndex(), i, i)
                del self._messages[i]
                self.endRemoveRows()
                return

    def edit_by_id(self, message_id: int, text: str) -> None:
        for i, s in enumerate(self._messages):
            if s.id == message_id:
                self._messages[i] = s.model_copy(update={"text": text})
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [self.TextRole])
                return


@dataclass(frozen=True)
class AttachmentItem:
    path: str
    mime_type: str

    @property
    def name(self) -> str:
        return Path(self.path).name

    @property
    def url(self) -> str:
        return Path(self.path).resolve().as_uri()

    @classmethod
    def from_path(cls, path: str) -> "AttachmentItem":
        mime, _ = guess_type(path)
        return cls(path=path, mime_type=mime or "application/octet-stream")

    @property
    def is_image(self) -> bool:
        return self.mime_type.startswith("image/")


class AttachmentListModel(QAbstractListModel):
    PathRole: int = Qt.ItemDataRole.UserRole + 1
    MimeTypeRole: int = Qt.ItemDataRole.UserRole + 2
    NameRole: int = Qt.ItemDataRole.UserRole + 3
    UrlRole: int = Qt.ItemDataRole.UserRole + 4
    IsImageRole: int = Qt.ItemDataRole.UserRole + 5

    countChanged: pyqtSignal = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[AttachmentItem] = []

    @property
    def attachments(self) -> list[AttachmentItem]:
        return self._items

    @override
    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.PathRole: QByteArray(b"path"),
            self.MimeTypeRole: QByteArray(b"mimeType"),
            self.NameRole: QByteArray(b"name"),
            self.UrlRole: QByteArray(b"url"),
            self.IsImageRole: QByteArray(b"isImage"),
        }

    @override
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    @override
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        match role:
            case self.PathRole:
                return item.path
            case self.MimeTypeRole:
                return item.mime_type
            case self.NameRole:
                return item.name
            case self.UrlRole:
                return item.url
            case self.IsImageRole:
                return item.is_image
        return None

    @pyqtProperty(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)

    def items(self) -> list[AttachmentItem]:
        return list(self._items)

    def add_path(self, path: str) -> None:
        if any(i.path == path for i in self._items):  # ignore duplicates
            return
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(AttachmentItem.from_path(path))
        self.endInsertRows()
        self.countChanged.emit()

    @pyqtSlot(int)
    def removeAt(self, row: int) -> None:
        if not 0 <= row < len(self._items):
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._items[row]
        self.endRemoveRows()
        self.countChanged.emit()

    def reset_to(self, attachments: list[AttachmentItem]) -> None:
        self.beginResetModel()
        self._items = list(attachments)
        self.endResetModel()
        self.countChanged.emit()

    def clear(self) -> None:
        if not self._items:
            return
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()
        self.countChanged.emit()
