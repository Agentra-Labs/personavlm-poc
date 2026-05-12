"""
PersonaVLM POC — Memory Layer (Remembering)
Persistent multimodal memory storage in SQLite.
Models the April email assistant scenario: stores compressed interaction memories
across sessions — recipient relationships, tone preferences, calendar patterns.
"""
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "persona_memory.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            memory_type TEXT NOT NULL CHECK(memory_type IN ('preference', 'interaction', 'relationship', 'pattern')),
            domain TEXT NOT NULL,
            content TEXT NOT NULL,
            importance REAL DEFAULT 0.5,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            session_id TEXT,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
        );
        CREATE TABLE IF NOT EXISTS memory_graph (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL REFERENCES memories(id),
            target_id INTEGER NOT NULL REFERENCES memories(id),
            relation TEXT NOT NULL,
            strength REAL DEFAULT 1.0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(source_id, target_id, relation)
        );
        CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories(user_id, memory_type);
        CREATE INDEX IF NOT EXISTS idx_memories_user_domain ON memories(user_id, domain);
    """)
    conn.commit()
    conn.close()


def create_user(user_id: str, name: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO user_profiles (user_id, name) VALUES (?, ?)",
        (user_id, name),
    )
    conn.commit()
    conn.close()


def store_memory(user_id: str, memory_type: str, domain: str,
                 content: str, importance: float = 0.5, session_id: str = "") -> int:
    """Store a compressed memory. Returns memory ID."""
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO memories (user_id, memory_type, domain, content, importance, session_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, memory_type, domain, content, importance, session_id),
    )
    conn.commit()
    mid = cur.lastrowid
    conn.close()
    return mid


def retrieve_memories(user_id: str, domain: str = "",
                      memory_type: str = "", limit: int = 10, session_id: str = "") -> list[dict]:
    """Retrieve relevant memories, ordered by importance and recency."""
    conn = get_conn()
    query = "SELECT * FROM memories WHERE user_id = ?"
    params = [user_id]
    if domain:
        query += " AND domain = ?"
        params.append(domain)
    if memory_type:
        query += " AND memory_type = ?"
        params.append(memory_type)
    query += " ORDER BY importance DESC, created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result


def link_memories(source_id: int, target_id: int, relation: str, strength: float = 1.0):
    """Create a relationship in the memory graph."""
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO memory_graph (source_id, target_id, relation, strength) VALUES (?, ?, ?, ?)",
        (source_id, target_id, relation, strength),
    )
    conn.commit()
    conn.close()


def get_related_memories(memory_id: int, relation: str = "") -> list[dict]:
    """Get memories linked to a given memory."""
    conn = get_conn()
    query = """
        SELECT m.*, mg.relation, mg.strength
        FROM memory_graph mg
        JOIN memories m ON m.id = mg.target_id
        WHERE mg.source_id = ?
    """
    params = [memory_id]
    if relation:
        query += " AND mg.relation = ?"
        params.append(relation)
    rows = conn.execute(query, params).fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result


def get_user_profile(user_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM user_profiles ORDER BY created_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
