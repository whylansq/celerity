import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "events.db"

def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _conn() as conn:
        conn.execute(
            'CREATE TABLE IF NOT EXISTS events ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT,'
            'ts REAL NOT NULL,'
            'event_type TEXT NOT NULL,'
            'node TEXT,'
            'detail TEXT)'
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ts ON events(ts)')
        conn.commit()

def log_event(event_type, node=None, detail=None):
    try:
        with _conn() as conn:
            conn.execute(
                'INSERT INTO events (ts, event_type, node, detail) VALUES (?, ?, ?, ?)',
                (time.time(), event_type, node, detail),
            )
            conn.commit()
    except Exception as e:
        print('[EVENTS] log error: ' + str(e))

def get_recent(limit=30, event_type=None):
    try:
        with _conn() as conn:
            if event_type:
                rows = conn.execute(
                    'SELECT * FROM events WHERE event_type=? ORDER BY ts DESC LIMIT ?',
                    (event_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM events ORDER BY ts DESC LIMIT ?', (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []

def format_events(limit=20):
    rows = get_recent(limit)
    if not rows:
        return 'История событий пуста'
    lines = ['ИСТОРИЯ СОБЫТИЙ']
    for r in rows:
        ts  = time.strftime('%d.%m %H:%M', time.localtime(r['ts']))
        et  = r['event_type']
        nd  = (' [' + r['node'] + ']') if r.get('node') else ''
        det = (' - ' + r['detail']) if r.get('detail') else ''
        lines.append(ts + nd + ' ' + et + det)
    return '\n'.join(lines)

init_db()
