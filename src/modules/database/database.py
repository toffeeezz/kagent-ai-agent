import atexit
import datetime
import sqlite3
from pathlib import Path
from typing import cast, final

import sqlite_vec

from modules.database.erros import DatabaseError
from modules.database.models import MemoryRow, MessageRow, SessionRow

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data/agent.db"

TEST_SCHEMA = """
PRAGMA foreign_keys = ON;   -- needed so deleting a session also deletes its messages

-- clean up earlier runs of this script
DELETE FROM sessions WHERE agent_name IN ('Ame', 'Amadeus');

-- sessions
INSERT INTO sessions (title, agent_name, created_at) VALUES
  ('Planning the QML layout', 'Ame',      '2026-09-28 09:00:00'),
  ('Memory design notes',     'Amadeus',  '2026-09-28 10:00:00');

-- messages for Ame
INSERT INTO messages (session_id, speaker_name, role, text, created_at) VALUES
  ((SELECT id FROM sessions WHERE agent_name = 'Ame'), 'John', 'user',
   'I want a left panel with my agents and a chat area on the right.', '2026-09-28 09:01:00'),
  ((SELECT id FROM sessions WHERE agent_name = 'Ame'), 'Ame', 'assistant',
   'Use a RowLayout: a fixed-width left panel and a chat area with Layout.fillWidth.', '2026-09-28 09:02:00'),
  ((SELECT id FROM sessions WHERE agent_name = 'Ame'), 'John', 'user',
   'How do I stop long agent names from stretching the panel?', '2026-09-28 09:03:00'),
  ((SELECT id FROM sessions WHERE agent_name = 'Ame'), 'Ame', 'assistant',
   'Set elide on the Text and give it Layout.fillWidth so the layout bounds its width.', '2026-09-28 09:04:00'),
  ((SELECT id FROM sessions WHERE agent_name = 'Ame'), 'John', 'user',
   'That worked, thanks.', '2026-09-28 09:05:00');

-- messages for Amadeus
INSERT INTO messages (session_id, speaker_name, role, text, created_at) VALUES
  ((SELECT id FROM sessions WHERE agent_name = 'Amadeus'), 'John', 'user',
   'Should memories be stored per agent or shared?', '2026-09-28 10:01:00'),
  ((SELECT id FROM sessions WHERE agent_name = 'Amadeus'), 'Amadeus', 'assistant',
   'Per agent is simpler: each memory row carries an agent_name and searches filter on it.', '2026-09-28 10:02:00'),
  ((SELECT id FROM sessions WHERE agent_name = 'Amadeus'), 'John', 'user',
   'And core memories?', '2026-09-28 10:03:00'),
  ((SELECT id FROM sessions WHERE agent_name = 'Amadeus'), 'Amadeus', 'assistant',
   'Keep a separate table of promoted memory ids, so promoting and demoting never touches the memory itself.', '2026-09-28 10:04:00'),
  ((SELECT id FROM sessions WHERE agent_name = 'Amadeus'), 'John', 'user',
   'Got it, that keeps things clean.', '2026-09-28 10:05:00');

-- check the result
SELECT s.agent_name, s.title, COUNT(m.id) AS messages
FROM sessions s LEFT JOIN messages m ON m.session_id = s.id
GROUP BY s.id;
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    speaker_name TEXT NOT NULL,
    role       TEXT NOT NULL,
    text       TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
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


def _to_message(row: dict[object, object]) -> MessageRow:
    data = dict(row)
    data["created_at"] = _utc_to_local_12h(str(data["created_at"]))
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
    def _one(
        self, sql: str, params: tuple[object, ...] = ()
    ) -> dict[object, object] | None:
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _all(
        self, sql: str, params: tuple[object, ...] = ()
    ) -> list[dict[object, object]]:
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
        self, session_id: int, role: str, text: str, speaker_name: str
    ) -> MessageRow:
        cur = self.conn.execute(
            "INSERT INTO messages (session_id, role, speaker_name, text) VALUES (?, ?, ?, ?)",
            (session_id, role, speaker_name, text),
        )
        self.conn.commit()
        if cur.lastrowid is None:
            raise DatabaseError("INSERT query did not return a row ID")
        message = self.get_message(cur.lastrowid)
        if message is None:
            raise DatabaseError("Could not read back the message that was just created")
        return message

    def get_messages(self, session_id: int) -> list[MessageRow]:
        rows = self._all(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id", (session_id,)
        )
        return [_to_message(r) for r in rows]

    def get_message(self, message_id: int) -> MessageRow | None:
        row = self._one("SELECT * FROM messages WHERE id = ?", (message_id,))
        return _to_message(row) if row else None


DATABASE = Database()
_ = atexit.register(DATABASE.close)
