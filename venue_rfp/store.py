"""SQLite-backed outreach tracking for the venue RFP tool.

One row per (venue_id, night). Statuses move left to right; notes and the
cover image URL are free-form and edited straight from the UI.
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

# Display labels — title-casing the raw keys turns "rfp_sent" into "Rfp Sent".
STATUS_LABELS = {
    'not_contacted': 'Not contacted',
    'rfp_sent': 'RFP sent',
    'replied': 'Replied',
    'proposal_received': 'Proposal received',
    'shortlisted': 'Shortlisted',
    'booked': 'Booked',
    'declined': 'Declined',
}

STATUSES = [
    'not_contacted',
    'rfp_sent',
    'replied',
    'proposal_received',
    'shortlisted',
    'booked',
    'declined',
]

_DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'outreach.db')
DB_PATH = os.environ.get('VENUE_DB_PATH', _DEFAULT_DB)

_lock = threading.Lock()


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outreach (
                venue_id     TEXT NOT NULL,
                night        TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'not_contacted',
                notes        TEXT NOT NULL DEFAULT '',
                sent_at      TEXT NOT NULL DEFAULT '',
                sender_id    TEXT NOT NULL DEFAULT '',
                updated_at   TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (venue_id, night)
            )
        """)
        _ensure_column(conn, 'outreach', 'sender_id')
        conn.execute("""
            CREATE TABLE IF NOT EXISTS venue_meta (
                venue_id     TEXT PRIMARY KEY,
                cover_image  TEXT NOT NULL DEFAULT '',
                email_override TEXT NOT NULL DEFAULT '',
                updated_at   TEXT NOT NULL DEFAULT ''
            )
        """)


def _ensure_column(conn, table, column):
    existing = {r['name'] for r in conn.execute(f'PRAGMA table_info({table})')}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def now():
    """Public alias — callers outside this module use this."""
    return _now()


def all_outreach():
    """Return {venue_id: {night: row}}."""
    with _connect() as conn:
        rows = conn.execute('SELECT * FROM outreach').fetchall()
    out = {}
    for r in rows:
        out.setdefault(r['venue_id'], {})[r['night']] = dict(r)
    return out


def all_meta():
    with _connect() as conn:
        rows = conn.execute('SELECT * FROM venue_meta').fetchall()
    return {r['venue_id']: dict(r) for r in rows}


def upsert_outreach(venue_id, night, **fields):
    allowed = {'status', 'notes', 'sent_at', 'sender_id'}
    fields = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if fields.get('status') and fields['status'] not in STATUSES:
        raise ValueError(f"unknown status: {fields['status']}")
    with _lock, _connect() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO outreach (venue_id, night, updated_at) VALUES (?,?,?)',
            (venue_id, night, _now()),
        )
        if fields:
            sets = ', '.join(f'{k} = ?' for k in fields)
            conn.execute(
                f'UPDATE outreach SET {sets}, updated_at = ? WHERE venue_id = ? AND night = ?',
                (*fields.values(), _now(), venue_id, night),
            )
        row = conn.execute(
            'SELECT * FROM outreach WHERE venue_id = ? AND night = ?', (venue_id, night)
        ).fetchone()
    return dict(row)


def upsert_meta(venue_id, **fields):
    allowed = {'cover_image', 'email_override'}
    fields = {k: v for k, v in fields.items() if k in allowed and v is not None}
    with _lock, _connect() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO venue_meta (venue_id, updated_at) VALUES (?,?)',
            (venue_id, _now()),
        )
        if fields:
            sets = ', '.join(f'{k} = ?' for k in fields)
            conn.execute(
                f'UPDATE venue_meta SET {sets}, updated_at = ? WHERE venue_id = ?',
                (*fields.values(), _now(), venue_id),
            )
        row = conn.execute(
            'SELECT * FROM venue_meta WHERE venue_id = ?', (venue_id,)
        ).fetchone()
    return dict(row)


def export_json():
    return json.dumps({'outreach': all_outreach(), 'meta': all_meta()}, indent=2)
