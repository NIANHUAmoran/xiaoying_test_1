import json
import sqlite3
from contextlib import contextmanager

from .domain import fingerprint, slot


class Store:
    def __init__(self, path, occupied=None):
        self.db = sqlite3.connect(path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS occupied(slot TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS drafts(
                id TEXT PRIMARY KEY, request_id TEXT NOT NULL, material_id TEXT NOT NULL,
                slot TEXT NOT NULL, confirmed INTEGER NOT NULL, body TEXT NOT NULL,
                UNIQUE(request_id, material_id));
            CREATE UNIQUE INDEX IF NOT EXISTS reserved_slot ON drafts(slot);
        """)
        self.db.commit()
        if occupied is not None:
            normalized = [(slot(x),) for x in occupied]
            with self.transaction():
                self.db.execute("DELETE FROM occupied")
                self.db.executemany("INSERT INTO occupied VALUES (?)", sorted(set(normalized)))

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def register(self, request):
        with self.transaction():
            row = self.db.execute("SELECT digest FROM requests WHERE id=?", (request["request_id"],)).fetchone()
            # Explicit user confirmation is an event on the same immutable request.
            original = {**request, "items": [{k: v for k, v in item.items() if k != "approved_slot"} for item in request["items"]]}
            digest = fingerprint(original)
            if row and row["digest"] != digest:
                raise ValueError("同一 request_id 的内容发生变化；修改请求请使用新 request_id")
            self.db.execute("INSERT OR IGNORE INTO requests VALUES (?,?)", (request["request_id"], digest))

    def busy(self, value, request_id, material_id):
        return bool(self.db.execute("SELECT 1 FROM occupied WHERE slot=?", (value,)).fetchone() or
                    self.db.execute("SELECT 1 FROM drafts WHERE slot=? AND NOT(request_id=? AND material_id=?)",
                                    (value, request_id, material_id)).fetchone())

    def occupy(self, value):
        self.db.execute("INSERT OR IGNORE INTO occupied VALUES (?)", (slot(value),))
        self.db.commit()

    def save(self, request_id, item, selected, confirmed):
        with self.transaction():
            row = self.db.execute("SELECT body FROM drafts WHERE request_id=? AND material_id=?",
                                  (request_id, item["material_id"])).fetchone()
            if self.busy(selected, request_id, item["material_id"]):
                return {"ok": False, "error": "slot_conflict_at_save"}
            previous = json.loads(row["body"]) if row else None
            if previous and previous["suggested_slot"] == selected and previous["confirmed"]:
                confirmed = True
            body = {"draft_id": "draft-" + fingerprint([request_id, item["material_id"]])[:20],
                    "material_id": item["material_id"], "requested_slot": slot(item["requested_slot"]),
                    "suggested_slot": selected, "confirmed": confirmed, "published": False}
            self.db.execute("""INSERT INTO drafts VALUES (?,?,?,?,?,?)
                ON CONFLICT(request_id, material_id) DO UPDATE SET
                slot=excluded.slot, confirmed=excluded.confirmed, body=excluded.body""",
                (body["draft_id"], request_id, item["material_id"], selected, int(confirmed),
                 json.dumps(body, ensure_ascii=False)))
            return {"ok": True, "duplicate": bool(row), "updated": bool(previous and previous != body), **body}
