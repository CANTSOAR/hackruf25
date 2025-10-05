# Ui/models.py
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chat.db")

# ---------------------- connection helpers ----------------------
def get_db():
    # allow cross-thread use in Flask debug server
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _column_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return any(r["name"] == col for r in cur.fetchall())

def _ensure_column(conn: sqlite3.Connection, table: str, col: str, decl: str):
    if not _column_exists(conn, table, col):
        cur = conn.cursor()
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        conn.commit()

def init_db():
    os.makedirs(BASE_DIR, exist_ok=True)
    conn = get_db()
    cur = conn.cursor()

    # Base tables (create if not exists)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_session TEXT,
            role TEXT NOT NULL,          -- 'user' | 'bot'
            text TEXT NOT NULL
        )
    """)
    conn.commit()

    # --- Lightweight migrations / column adds ---
    # users: avatar prefs
    _ensure_column(conn, "users", "avatar_gender", "TEXT DEFAULT 'person'")
    _ensure_column(conn, "users", "avatar_tone",   "TEXT DEFAULT 'default'")
    cur.execute("UPDATE users SET avatar_gender = COALESCE(avatar_gender, 'person')")
    cur.execute("UPDATE users SET avatar_tone   = COALESCE(avatar_tone,   'default')")

    # messages: ISO timestamp column `ts`
    _ensure_column(conn, "messages", "ts", "TEXT")
    # backfill any NULL/empty ts with a proper ISO (UTC) string
    cur.execute("""
        UPDATE messages
        SET ts = COALESCE(NULLIF(ts,''), strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        WHERE ts IS NULL OR ts = ''
    """)

    conn.commit()
    conn.close()  # close setup connection

# ---------------------- models ----------------------
@dataclass
class User:
    id: int
    username: str
    name: str
    password_hash: str
    avatar_gender: str = "person"
    avatar_tone: str = "default"

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> "User":
        return User(
            id=row["id"],
            username=row["username"],
            name=row["name"],
            password_hash=row["password_hash"],
            avatar_gender=row["avatar_gender"],
            avatar_tone=row["avatar_tone"],
        )

    @staticmethod
    def get_by_username(db, username: str) -> Optional["User"]:
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        return User._row_to_user(row) if row else None

    @staticmethod
    def create(db, username: str, name: str, password_hash: str) -> Optional["User"]:
        try:
            cur = db.cursor()
            cur.execute(
                "INSERT INTO users (username, name, password_hash) VALUES (?,?,?)",
                (username, name, password_hash),
            )
            db.commit()
            uid = cur.lastrowid
            return User(id=uid, username=username, name=name, password_hash=password_hash)
        except sqlite3.IntegrityError:
            return None

    def update_preferences(self, db, avatar_gender: str, avatar_tone: str) -> None:
        cur = db.cursor()
        cur.execute(
            "UPDATE users SET avatar_gender=?, avatar_tone=? WHERE id=?",
            (avatar_gender, avatar_tone, self.id),
        )
        db.commit()
        self.avatar_gender = avatar_gender
        self.avatar_tone = avatar_tone


@dataclass
class Message:
    id: int
    user_id: int
    role: str
    text: str
    timestamp: datetime
    chat_session: Optional[str] = None

    @staticmethod
    def create(db, user_id: int, role: str, text: str, chat_session: Optional[str]) -> "Message":
        now_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        cur = db.cursor()
        cur.execute(
            "INSERT INTO messages (user_id, chat_session, role, text, ts) VALUES (?,?,?,?,?)",
            (user_id, chat_session, role, text, now_iso),
        )
        db.commit()
        mid = cur.lastrowid
        return Message(
            id=mid,
            user_id=user_id,
            role=role,
            text=text,
            chat_session=chat_session,
            timestamp=datetime.fromisoformat(now_iso.replace("Z", "")),
        )

    @staticmethod
    def get_messages(
        db,
        user_id: int,
        chat_session: Optional[str] = None,
        before: Optional[str] = None,
        limit: int = 20,
    ) -> List["Message"]:
        params = [user_id]
        sql = "SELECT * FROM messages WHERE user_id=?"
        if chat_session:
            sql += " AND chat_session=?"
            params.append(chat_session)
        if before:
            sql += " AND ts < ?"
            params.append(before)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        cur = db.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

        out = []
        for r in rows:
            ts = r["ts"]
            try:
                dt = datetime.fromisoformat(ts.replace("Z", ""))
            except Exception:
                dt = datetime.utcnow()
            out.append(Message(
                id=r["id"],
                user_id=r["user_id"],
                role=r["role"],
                text=r["text"],
                chat_session=r["chat_session"],
                timestamp=dt,
            ))
        return out