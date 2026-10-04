import datetime
import logging
from collections.abc import Sequence
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

from modules.agents.builder import AGENT_AVATAR_DIR
from modules.agents.models import AgentDefinition
from modules.database.models import MessageRow, SessionRow

logger = logging.getLogger(__name__)


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
        return 0 if parent.isValid() else len(self._agents)

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

    def add(self, agent_definitions: list[AgentDefinition]) -> None:
        for agent in agent_definitions:
            if agent.type == "basic":
                continue
            image = (
                AGENT_AVATAR_DIR / agent.image_path
                if agent.image_path
                else AGENT_AVATAR_DIR / "placeholder.png"
            )

            if not image.exists():
                logger.warning("Agent image not found: %s", image)
                image = AGENT_AVATAR_DIR / "placeholder.png"
            pos = len(self._agents)
            self.beginInsertRows(QModelIndex(), pos, pos)
            self._agents.append({"agentName": agent.name, "imagePath": str(image)})
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
                self._sessions[i] = s.model_copy(update={"title": title})
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [self.TitleRole])
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

    @property
    def is_image(self) -> bool:
        return self.mime_type.startswith("image/")

    @classmethod
    def from_path(cls, path: str) -> "AttachmentItem":
        mime, _ = guess_type(path)
        return cls(path=path, mime_type=mime or "application/octet-stream")


class MessageListModel(QAbstractListModel):
    TextRole: int = Qt.ItemDataRole.UserRole + 1
    IdRole: int = Qt.ItemDataRole.UserRole + 2
    RoleRole: int = Qt.ItemDataRole.UserRole + 3
    AttachmentsRole: int = Qt.ItemDataRole.UserRole + 4

    countChanged: pyqtSignal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._messages: list[MessageRow] = []
        self._last_pending_id = 0

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

    @pyqtProperty(int, notify=countChanged)
    def count(self) -> int:
        return len(self._messages)

    def reset_to(self, messages: list[MessageRow]) -> None:
        self.beginResetModel()
        self._messages = list(messages)
        self.endResetModel()
        self.countChanged.emit()

    def append(self, message: MessageRow) -> None:
        row = len(self._messages)
        self.beginInsertRows(QModelIndex(), row, row)
        self._messages.append(message)
        self.endInsertRows()
        self.countChanged.emit()

    def add_pending(
        self,
        session_id: int,
        speaker_name: str,
        text: str,
        attachments: Sequence[AttachmentItem] = (),
    ) -> int:
        """Show a user message before it's saved. Returns its temporary id."""
        self._last_pending_id -= 1
        pending_id = self._last_pending_id
        self.append(
            MessageRow(
                id=pending_id,
                session_id=session_id,
                role="user",
                speaker_name=speaker_name,
                text=text,
                created_at=datetime.datetime.now(datetime.UTC).isoformat(
                    sep=" ", timespec="seconds"
                ),
                attachments=tuple(a.path for a in attachments),
            )
        )
        return pending_id

    def confirm_pending(self, pending_id: int, saved: MessageRow) -> None:
        """Replace a pending row with the saved one. No-op if it's gone
        (e.g. the model was reset by a session switch)."""
        for i, m in enumerate(self._messages):
            if m.id == pending_id:
                self._messages[i] = saved
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [])
                return

    def remove_by_id(self, message_id: int) -> None:
        for i, s in enumerate(self._messages):
            if s.id == message_id:
                self.beginRemoveRows(QModelIndex(), i, i)
                del self._messages[i]
                self.endRemoveRows()
                self.countChanged.emit()
                return

    def edit_by_id(self, message_id: int, text: str) -> None:
        for i, s in enumerate(self._messages):
            if s.id == message_id:
                self._messages[i] = s.model_copy(update={"text": text})
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [self.TextRole])
                return


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

    # ---------- called from QML ----------
    @pyqtSlot("QVariantList")
    def addUrls(self, urls: list[Any]) -> None:
        for u in urls:
            url = u if isinstance(u, QUrl) else QUrl(str(u))
            path = url.toLocalFile()
            if path:  # ignore non-local URLs
                self.add_path(path)

    @pyqtSlot(int)
    def removeAt(self, row: int) -> None:
        if not 0 <= row < len(self._items):
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._items[row]
        self.endRemoveRows()
        self.countChanged.emit()

    # ---------- called from Python ----------
    def add_path(self, path: str) -> None:
        if any(i.path == path for i in self._items):  # ignore duplicates
            return
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(AttachmentItem.from_path(path))
        self.endInsertRows()
        self.countChanged.emit()

    def take(self) -> list[AttachmentItem]:
        """Snapshot the current attachments and clear the list."""
        items = list(self._items)
        self.clear()
        return items

    def restore(self, items: Sequence[AttachmentItem]) -> None:
        """Put attachments back (after a failed send), keeping anything the
        user attached in the meantime."""
        restored = list(items)
        known = {i.path for i in restored}
        merged = restored + [i for i in self._items if i.path not in known]
        self.beginResetModel()
        self._items = merged
        self.endResetModel()
        self.countChanged.emit()

    def clear(self) -> None:
        if not self._items:
            return
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()
        self.countChanged.emit()
