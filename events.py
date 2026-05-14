cat > /opt/opsbot/events.py << 'EOF'
"""
SQLite-backed event log.
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "events.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         REAL    NOT NULL,
                event_type TEXT    NOT NULL,
                node       TEXT,
                detail     TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON events(ts)")
        conn.commit()


def log_event(event_type: str, node: str | None = None, detail: str | None = None):
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO events (ts, event_type, node, detail) VALUES (?, ?, ?, ?)",
                (time.time(), event_type, node, detail),
            )
            conn.commit()
    except Exception as e:
        print(f"[EVENTS] log error: {e}")


def get_recent(limit: int = 30, event_type: str | None = None) -> list[dict]:
    try:
        with _conn() as conn:
            if event_type:
                rows = conn.execute(
                    "SELECT * FROM events WHERE event_type=? ORDER BY ts DESC LIMIT ?",
                    (event_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM events ORDER BY ts DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def format_events(limit: int = 20) -> str:
    rows = get_recent(limit)
    if not rows:
        return "📋 История событий пуста"

    lines = [f"📋 ИСТОРИЯ СОБЫТИЙ (последние {limit})\n"]
    for r in rows:
        ts  = time.strftime("%d.%m %H:%M", time.localtime(r["ts"]))
        et  = r["event_type"]
        nd  = f" [{r['node']}]" if r.get("node") else ""
        det = f" — {r['detail']}" if r.get("detail") else ""

        icon = {
            "node_down":    "🔴",
            "node_up":      "🟢",
            "node_restart": "🔄",
            "spike":        "🚨",
            "user_create":  "➕",
            "user_delete":  "🗑",
            "auth_fail":    "⛔",
            "ssh_error":    "💻❌",
            "backup":       "💾",
        }.get(et, "•")

        lines.append(f"{icon} {ts}{nd} {et}{det}")

    return "\n".join(lines)


init_db()
EOF
