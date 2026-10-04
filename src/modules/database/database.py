import atexit
import datetime
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any, final

from modules.database.erros import DatabaseError
from modules.database.models import MessageRow, SessionRow

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data/agent.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    speaker_name TEXT NOT NULL,
    role         TEXT NOT NULL,
    text         TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attachments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    path       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments(message_id);
"""

MESSAGE_TIME_FORMAT = "%b %d, %I:%M %p"


def _utc_to_local_12h(utc_text: str) -> str:
    """'2026-10-02 06:57:17' (UTC, as SQLite's CURRENT_TIMESTAMP stores it)
    -> a 12-hour string in the machine's local timezone.
    Falls back to the raw text if it can't be parsed."""
    try:
        utc_time = datetime.datetime.fromisoformat(utc_text).replace(
            tzinfo=datetime.UTC
        )
    except ValueError:
        return utc_text
    return utc_time.astimezone().strftime(MESSAGE_TIME_FORMAT)


def _to_message(row: dict[str, Any], attachments: Sequence[str] = ()) -> MessageRow:
    data = dict(row)
    data["created_at"] = _utc_to_local_12h(str(data["created_at"]))
    data["attachments"] = tuple(attachments)
    return MessageRow.model_validate(data)


@final
class Database:
    def __init__(self) -> None:
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

        _ = self.conn.execute("PRAGMA foreign_keys = ON")
        _ = self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ---------- low-level helpers ----------
    def _one(self, sql: str, params: tuple[object, ...] = ()) -> dict[str, Any] | None:
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _all(self, sql: str, params: tuple[object, ...] = ()) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    # ---------- sessions ----------
    def create_session(self, title: str, agent_name: str) -> SessionRow:
        cur = self.conn.execute(
            "INSERT INTO sessions (title, agent_name) VALUES (?, ?)",
            (title, agent_name),
        )
        self.conn.commit()
        if cur.lastrowid is None:
            raise DatabaseError("INSERT query did not return a row ID")
        session = self.get_session(cur.lastrowid)
        if session is None:
            raise DatabaseError("Could not read back the session that was just created")
        return session

    def get_session(self, session_id: int) -> SessionRow | None:
        row = self._one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        return SessionRow.model_validate(row) if row else None

    def get_session_list(self, agent_name: str) -> list[SessionRow]:
        rows = self._all(
            "SELECT * FROM sessions WHERE agent_name = ? ORDER BY created_at DESC, id DESC",
            (agent_name,),
        )
        return [SessionRow.model_validate(row) for row in rows]

    def delete_session(self, session_id: int) -> None:
        cur = self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()
        if cur.rowcount == 0:
            raise DatabaseError(f"No session found with id {session_id}")

    # ---------- messages ----------
    def add_message(
        self,
        session_id: int,
        role: str,
        text: str,
        speaker_name: str,
        attachments: Sequence[str] = (),
    ) -> MessageRow:
        # so a message can never be saved without its attachments.
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO messages (session_id, role, speaker_name, text) VALUES (?, ?, ?, ?)",
                (session_id, role, speaker_name, text),
            )
            message_id = cur.lastrowid
            if message_id is None:
                raise DatabaseError("INSERT query did not return a row ID")
            if attachments:
                _ = self.conn.executemany(
                    "INSERT INTO attachments (message_id, path) VALUES (?, ?)",
                    [(message_id, p) for p in attachments],
                )
        message = self.get_message(message_id)
        if message is None:
            raise DatabaseError("Could not read back the message that was just created")
        return message

    def get_messages(self, session_id: int) -> list[MessageRow]:
        rows = self._all(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id", (session_id,)
        )
        # One query for all attachments in the session, grouped by message
        grouped: dict[int, list[str]] = {}
        for a in self._all(
            """SELECT a.message_id, a.path FROM attachments a 
            JOIN messages m ON m.id = a.message_id 
            WHERE m.session_id = ? ORDER BY a.id""",
            (session_id,),
        ):
            grouped.setdefault(a["message_id"], []).append(a["path"])
        return [_to_message(r, grouped.get(r["id"], [])) for r in rows]

    def get_message(self, message_id: int) -> MessageRow | None:
        row = self._one("SELECT * FROM messages WHERE id = ?", (message_id,))
        if row is None:
            return None
        paths = [
            a["path"]
            for a in self._all(
                "SELECT path FROM attachments WHERE message_id = ? ORDER BY id",
                (message_id,),
            )
        ]
        return _to_message(row, paths)


DATABASE = Database()
_ = atexit.register(DATABASE.close)
