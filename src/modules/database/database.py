import sqlite3
from pathlib import Path
from typing import cast, final

import sqlite_vec

from modules.database.erros import DatabaseError
from modules.database.models import MemoryRow, MessageRow, SessionRow

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data/agent.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT,
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

CREATE TABLE IF NOT EXISTS memories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name      TEXT NOT NULL,
    text            TEXT NOT NULL,
    importance      REAL,
    retrieval_score REAL DEFAULT 0,
    last_accessed   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core_memories (
    memory_id   INTEGER PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
    promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_messages (
    memory_id  INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    PRIMARY KEY (memory_id, message_id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS vec_memories USING vec0(
    embedding float[4096] distance_metric=cosine
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
CREATE INDEX IF NOT EXISTS idx_memory_messages_message ON memory_messages(message_id);
CREATE INDEX IF NOT EXISTS idx_memory_messages_memory ON memory_messages(memory_id);
"""


@final
class Database:
    def __init__(self) -> None:
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)

        _ = self.conn.execute("PRAGMA foreign_keys = ON")
        _ = self.conn.executescript(SCHEMA)
        self.conn.commit()

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
    def create_session(self, title: str | None = None) -> int:
        cur = self.conn.execute("INSERT INTO sessions (title) VALUES (?)", (title,))
        self.conn.commit()
        if cur.lastrowid is None:
            raise DatabaseError("INSERT query did not return a row ID")
        return cur.lastrowid

    def get_session(self, session_id: int) -> SessionRow | None:
        row = self._one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        return SessionRow.model_validate(row) if row else None

    # ---------- messages ----------
    def add_message(
        self, session_id: int, role: str, text: str, agent_name: str | None = None
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO messages (session_id, role, agent_name, text) VALUES (?, ?, ?, ?)",
            (session_id, role, agent_name, text),
        )
        self.conn.commit()
        if cur.lastrowid is None:
            raise DatabaseError("INSERT did not return a row ID")
        return cur.lastrowid

    def get_messages(self, session_id: int) -> list[MessageRow]:
        rows = self._all(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id", (session_id,)
        )
        return [MessageRow.model_validate(r) for r in rows]

    # ---------- memories ----------
    def add_memory(
        self,
        text: str,
        agent_name: str,
        embedding: list[float] | None = None,
        importance: float | None = None,
        source_message_ids: tuple[int, ...] = (),
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO memories (text, agent_name, importance) VALUES (?, ?, ?)",
            (text, agent_name, importance),
        )
        if cur.lastrowid is None:
            self.conn.rollback()
            raise DatabaseError("INSERT query did not return a row ID")
        memory_id = cur.lastrowid

        if embedding is not None:
            _ = self.conn.execute(
                "INSERT INTO vec_memories(rowid, embedding) VALUES (?, ?)",
                (memory_id, sqlite_vec.serialize_float32(embedding)),
            )
        for message_id in source_message_ids:
            _ = self.conn.execute(
                "INSERT OR IGNORE INTO memory_messages (memory_id, message_id) VALUES (?, ?)",
                (memory_id, message_id),
            )

        self.conn.commit()
        return memory_id

    def get_memory(self, memory_id: int) -> MemoryRow | None:
        row = self._one("SELECT * FROM memories WHERE id = ?", (memory_id,))
        return MemoryRow.model_validate(row) if row else None

    def delete_memory(self, memory_id: int) -> None:
        _ = self.conn.execute("DELETE FROM vec_memories WHERE rowid = ?", (memory_id,))
        cur = self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()
        if cur.rowcount == 0:
            raise DatabaseError(f"No memory found with id {memory_id}")

    def get_source_messages(self, memory_id: int) -> list[MessageRow]:
        rows = self._all(
            """
            SELECT msg.* FROM messages msg
            JOIN memory_messages mm ON mm.message_id = msg.id
            WHERE mm.memory_id = ?
            ORDER BY msg.id
            """,
            (memory_id,),
        )
        return [MessageRow.model_validate(r) for r in rows]

    def search_memories(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[MemoryRow]:
        knn = self._all(
            "SELECT rowid, distance FROM vec_memories WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (sqlite_vec.serialize_float32(query_embedding), top_k),
        )
        if not knn:
            return []
        ids = [r["rowid"] for r in knn]
        marks = ",".join("?" * len(ids))
        rows = self._all(f"SELECT * FROM memories WHERE id IN ({marks})", tuple(ids))

        dist_by_id: dict[object, float] = {
            r["rowid"]: cast(float, r["distance"]) for r in knn
        }
        rows.sort(key=lambda r: dist_by_id[r["id"]])
        return [MemoryRow.model_validate(r) for r in rows]

    # ---------- core memories ----------
    def promote_to_core(self, memory_id: int) -> None:
        _ = self.conn.execute(
            "INSERT OR IGNORE INTO core_memories (memory_id) VALUES (?)", (memory_id,)
        )
        self.conn.commit()

    def demote_from_core(self, memory_id: int) -> None:
        _ = self.conn.execute(
            "DELETE FROM core_memories WHERE memory_id = ?", (memory_id,)
        )
        self.conn.commit()

    def is_core(self, memory_id: int) -> bool:
        return (
            self._one("SELECT 1 FROM core_memories WHERE memory_id = ?", (memory_id,))
            is not None
        )

    def get_core_memories(self) -> list[MemoryRow]:
        rows = self._all(
            """
            SELECT m.* FROM memories m
            JOIN core_memories c ON c.memory_id = m.id
            ORDER BY c.promoted_at
            """
        )
        return [MemoryRow.model_validate(r) for r in rows]


DATABASE = Database()
