import atexit
import datetime
import sqlite3
import struct
from collections.abc import Sequence
from pathlib import Path
from typing import Any, final

import sqlite_vec

from modules.database.erros import DatabaseError
from modules.database.models import MemoryRow, MessageRow, SessionRow

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data/agent.db"

EMBEDDING_DIM = 4096

# ---------- memory ranking ----------
# score = W_RELEVANCE * similarity + W_IMPORTANCE * importance + W_RECALL * effective_recall
W_RELEVANCE: float = 0.60
W_IMPORTANCE: float = 0.25
W_RECALL: float = 0.15
MIN_SIMILARITY: float = 0.35  # below this a memory is treated as unrelated
RECALL_HALF_LIFE_DAYS: float = 14.0  # recall_score halves after this many idle days
RECALL_BOOST: float = 0.2  # added to the (decayed) recall score on each recall

SCHEMA = f"""
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

CREATE TABLE IF NOT EXISTS memories (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name       TEXT NOT NULL,
    content          TEXT NOT NULL,
    recall_score     REAL NOT NULL DEFAULT 1.0 CHECK (recall_score BETWEEN 0 AND 1),
    importance       REAL NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- many-to-many: one memory can come from several messages and
-- one message can produce several memories
CREATE TABLE IF NOT EXISTS memory_messages (
    memory_id  INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    PRIMARY KEY (memory_id, message_id)
);

-- sqlite-vec virtual table. memory_id mirrors memories.id
CREATE VIRTUAL TABLE IF NOT EXISTS memory_embeddings USING vec0(
    memory_id INTEGER PRIMARY KEY,
    embedding float[{EMBEDDING_DIM}] distance_metric=cosine
);

-- virtual tables can't have foreign keys, so this keeps embeddings in sync
CREATE TRIGGER IF NOT EXISTS trg_memories_delete_embedding
AFTER DELETE ON memories
BEGIN
    DELETE FROM memory_embeddings WHERE memory_id = OLD.id;
END;

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments(message_id);
CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent_name, id);
CREATE INDEX IF NOT EXISTS idx_memory_messages_message ON memory_messages(message_id);
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


def _to_memory(row: dict[str, Any], message_ids: Sequence[int] = ()) -> MemoryRow:
    data = dict(row)
    _ = data.pop("idle_days", None)  # internal, only used for ranking
    data["created_at"] = _utc_to_local_12h(str(data["created_at"]))
    data["last_accessed_at"] = _utc_to_local_12h(str(data["last_accessed_at"]))
    data["message_ids"] = tuple(message_ids)
    return MemoryRow.model_validate(
        data
    )  # distance/similarity/score pass through if present


def _check_score(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise DatabaseError(f"{name} must be between 0 and 1, got {value}")


def _serialize_embedding(embedding: Sequence[float]) -> bytes:
    if len(embedding) != EMBEDDING_DIM:
        raise DatabaseError(
            f"Embedding has {len(embedding)} dimensions, expected {EMBEDDING_DIM}"
        )
    return sqlite_vec.serialize_float32(list(embedding))


def _effective_recall(recall_score: float, idle_days: float | None) -> float:
    """recall_score decayed by time since last access (exponential, half-life based)."""
    days = max(0.0, idle_days or 0.0)
    return recall_score * 0.5 ** (days / RECALL_HALF_LIFE_DAYS)


def _similarity(distance: float | None) -> float:
    """Cosine distance (0..2) -> similarity clamped to 0..1."""
    if distance is None:
        return 0.0
    return max(0.0, min(1.0, 1.0 - distance))


def _memory_score(
    similarity: float, importance: float, effective_recall: float
) -> float:
    return (
        W_RELEVANCE * similarity
        + W_IMPORTANCE * importance
        + W_RECALL * effective_recall
    )


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

    def rename_session(self, title: str, session_id: int) -> None:
        cur = self.conn.execute(
            "UPDATE sessions SET title = ? WHERE id = ?", (title, session_id)
        )
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

    # ---------- memories ----------
    def _hydrate_memories(self, rows: list[dict[str, Any]]) -> list[MemoryRow]:
        """Attach linked message ids to memory rows with one extra query."""
        if not rows:
            return []
        ids = [r["id"] for r in rows]
        marks = ",".join("?" * len(ids))
        grouped: dict[int, list[int]] = {}
        for link in self._all(
            f"""SELECT memory_id, message_id FROM memory_messages
            WHERE memory_id IN ({marks}) ORDER BY message_id""",
            tuple(ids),
        ):
            grouped.setdefault(link["memory_id"], []).append(link["message_id"])
        return [_to_memory(r, grouped.get(r["id"], [])) for r in rows]

    def add_memory(
        self,
        agent_name: str,
        content: str,
        embedding: Sequence[float],
        importance: float = 0.5,
        recall_score: float = 1.0,
        message_ids: Sequence[int] = (),
    ) -> MemoryRow:
        """Store a memory, its source-message links, and its embedding atomically."""
        _check_score("importance", importance)
        _check_score("recall_score", recall_score)
        blob = _serialize_embedding(embedding)

        with self.conn:
            cur = self.conn.execute(
                """INSERT INTO memories
                (agent_name, content, recall_score, importance, last_accessed_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (agent_name, content, recall_score, importance),
            )
            memory_id = cur.lastrowid
            if memory_id is None:
                raise DatabaseError("INSERT query did not return a row ID")
            if message_ids:
                _ = self.conn.executemany(
                    "INSERT OR IGNORE INTO memory_messages (memory_id, message_id) VALUES (?, ?)",
                    [(memory_id, mid) for mid in message_ids],
                )
            _ = self.conn.execute(
                "INSERT INTO memory_embeddings (memory_id, embedding) VALUES (?, ?)",
                (memory_id, blob),
            )
        memory = self.get_memory(memory_id)
        if memory is None:
            raise DatabaseError("Could not read back the memory that was just created")
        return memory

    def get_memory(self, memory_id: int) -> MemoryRow | None:
        row = self._one("SELECT * FROM memories WHERE id = ?", (memory_id,))
        if row is None:
            return None
        return self._hydrate_memories([row])[0]

    def get_memory_list(
        self, agent_name: str, limit: int | None = None
    ) -> list[MemoryRow]:
        sql = "SELECT * FROM memories WHERE agent_name = ? ORDER BY id DESC"
        params: tuple[object, ...] = (agent_name,)
        if limit is not None:
            sql += " LIMIT ?"
            params = (agent_name, limit)
        return self._hydrate_memories(self._all(sql, params))

    def update_memory_scores(
        self,
        memory_id: int,
        *,
        recall_score: float | None = None,
        importance: float | None = None,
    ) -> None:
        """Set scores directly. Does NOT touch last_accessed_at
        (use reinforce_memory for 'this memory was just used')."""
        sets: list[str] = []
        params: list[object] = []
        if recall_score is not None:
            _check_score("recall_score", recall_score)
            sets.append("recall_score = ?")
            params.append(recall_score)
        if importance is not None:
            _check_score("importance", importance)
            sets.append("importance = ?")
            params.append(importance)
        if not sets:
            raise DatabaseError(
                "Nothing to update: pass recall_score and/or importance"
            )

        cur = self.conn.execute(
            f"UPDATE memories SET {', '.join(sets)} WHERE id = ?",
            (*params, memory_id),
        )
        self.conn.commit()
        if cur.rowcount == 0:
            raise DatabaseError(f"No memory found with id {memory_id}")

    def reinforce_memory(
        self,
        memory_id: int,
        boost: float = RECALL_BOOST,
        importance: float | None = None,
    ) -> None:
        """Mark a memory as used: boost its decayed recall score, reset the
        decay clock (last_accessed_at), and optionally raise its importance."""
        row = self._one(
            """SELECT recall_score, importance,
            julianday('now') - julianday(last_accessed_at) AS idle_days
            FROM memories WHERE id = ?""",
            (memory_id,),
        )
        if row is None:
            raise DatabaseError(f"No memory found with id {memory_id}")
        new_recall = min(
            1.0, _effective_recall(row["recall_score"], row["idle_days"]) + boost
        )
        new_importance = row["importance"]
        if importance is not None:
            _check_score("importance", importance)
            new_importance = max(new_importance, importance)
        _ = self.conn.execute(
            """UPDATE memories
            SET recall_score = ?, importance = ?, last_accessed_at = CURRENT_TIMESTAMP
            WHERE id = ?""",
            (new_recall, new_importance, memory_id),
        )
        self.conn.commit()

    def delete_memory(self, memory_id: int) -> None:
        # The trigger removes the embedding; ON DELETE CASCADE removes the links.
        cur = self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()
        if cur.rowcount == 0:
            raise DatabaseError(f"No memory found with id {memory_id}")

    # ---------- memory <-> message links ----------
    def link_memory_message(self, memory_id: int, message_id: int) -> None:
        _ = self.conn.execute(
            "INSERT OR IGNORE INTO memory_messages (memory_id, message_id) VALUES (?, ?)",
            (memory_id, message_id),
        )
        self.conn.commit()

    def get_memory_messages(self, memory_id: int) -> list[MessageRow]:
        """The messages a memory was formed from."""
        ids = [
            r["message_id"]
            for r in self._all(
                "SELECT message_id FROM memory_messages WHERE memory_id = ? ORDER BY message_id",
                (memory_id,),
            )
        ]
        return [m for mid in ids if (m := self.get_message(mid)) is not None]

    def get_message_memories(self, message_id: int) -> list[MemoryRow]:
        """The memories that were formed from a message."""
        rows = self._all(
            """SELECT m.* FROM memories m
            JOIN memory_messages mm ON mm.memory_id = m.id
            WHERE mm.message_id = ? ORDER BY m.id""",
            (message_id,),
        )
        return self._hydrate_memories(rows)

    # ---------- embeddings ----------
    def set_embedding(self, memory_id: int, embedding: Sequence[float]) -> None:
        """Replace a memory's embedding (e.g. after switching embedding models)."""
        blob = _serialize_embedding(embedding)
        if self._one("SELECT 1 FROM memories WHERE id = ?", (memory_id,)) is None:
            raise DatabaseError(f"No memory found with id {memory_id}")
        with self.conn:
            _ = self.conn.execute(
                "DELETE FROM memory_embeddings WHERE memory_id = ?", (memory_id,)
            )
            _ = self.conn.execute(
                "INSERT INTO memory_embeddings (memory_id, embedding) VALUES (?, ?)",
                (memory_id, blob),
            )

    def get_embedding(self, memory_id: int) -> list[float] | None:
        row = self._one(
            "SELECT embedding FROM memory_embeddings WHERE memory_id = ?", (memory_id,)
        )
        if row is None:
            return None
        return list(struct.unpack(f"{EMBEDDING_DIM}f", row["embedding"]))

    # ---------- memory search ----------
    def _knn(
        self,
        agent_name: str,
        query_embedding: Sequence[float],
        limit: int,
        oversample: int = 4,
    ) -> list[dict[str, Any]]:
        """Raw nearest-neighbour rows for one agent, closest first.
        Includes `distance` and `idle_days` columns."""
        blob = _serialize_embedding(query_embedding)
        return self._all(
            """
            WITH knn AS (
                SELECT memory_id, distance
                FROM memory_embeddings
                WHERE embedding MATCH ? AND k = ?
            )
            SELECT m.*, knn.distance AS distance,
                   julianday('now') - julianday(m.last_accessed_at) AS idle_days
            FROM knn
            JOIN memories m ON m.id = knn.memory_id
            WHERE m.agent_name = ?
            ORDER BY knn.distance
            LIMIT ?
            """,
            (blob, limit * oversample, agent_name, limit),
        )

    def search_memories(
        self,
        agent_name: str,
        query_embedding: Sequence[float],
        limit: int = 5,
        oversample: int = 4,
    ) -> list[MemoryRow]:
        """Pure similarity search, closest first. No ranking formula, no side effects.
        `distance` is cosine distance (0 = identical, 2 = opposite)."""
        rows = self._knn(agent_name, query_embedding, limit, oversample)
        for row in rows:
            row["similarity"] = _similarity(row["distance"])
        return self._hydrate_memories(rows)

    def recall_memories(
        self,
        agent_name: str,
        query_embedding: Sequence[float],
        limit: int = 5,
        candidates: int = 20,
        min_similarity: float = MIN_SIMILARITY,
        reinforce: bool = True,
    ) -> list[MemoryRow]:
        """Ranked recall:
            score = 0.60 * similarity + 0.25 * importance + 0.15 * effective_recall
        Memories below `min_similarity` are dropped first. Returned memories are
        reinforced (recall boosted, last_accessed_at reset) unless reinforce=False.
        The returned rows show values as they were *before* reinforcement."""
        rows = self._knn(agent_name, query_embedding, candidates)

        ranked: list[tuple[float, float, dict[str, Any]]] = []
        for row in rows:
            sim = _similarity(row["distance"])
            if sim < min_similarity:
                continue
            eff = _effective_recall(row["recall_score"], row["idle_days"])
            row["similarity"] = sim
            row["score"] = _memory_score(sim, row["importance"], eff)
            ranked.append((row["score"], eff, row))

        ranked.sort(key=lambda item: item[0], reverse=True)
        top = ranked[:limit]

        if reinforce and top:
            with self.conn:
                _ = self.conn.executemany(
                    """UPDATE memories
                    SET recall_score = ?, last_accessed_at = CURRENT_TIMESTAMP
                    WHERE id = ?""",
                    [(min(1.0, eff + RECALL_BOOST), row["id"]) for _, eff, row in top],
                )

        return self._hydrate_memories([row for _, _, row in top])


DATABASE = Database()
_ = atexit.register(DATABASE.close)
