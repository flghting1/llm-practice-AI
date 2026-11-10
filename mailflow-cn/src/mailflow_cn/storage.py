"""SQLite work queue and immutable review events; review is optimistic and single-use."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone


class ReviewConflict(Exception):
    pass


class Repository:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.RLock()
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        with self.db:
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS mail_items (id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE, created_at TEXT, status TEXT, version INTEGER, payload TEXT)"
            )
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS review_events (id TEXT PRIMARY KEY, item_id TEXT, created_at TEXT, payload TEXT)"
            )

    def find(self, email: dict):
        fingerprint = self.fingerprint(email)
        with self.lock:
            row = self.db.execute(
                "SELECT id FROM mail_items WHERE fingerprint=?", (fingerprint,)
            ).fetchone()
        return self.get(row["id"]) if row else None

    @staticmethod
    def fingerprint(email):
        return hashlib.sha256(
            json.dumps(email, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()

    def add(self, result):
        key, now = uuid.uuid4().hex, datetime.now(timezone.utc).isoformat()
        with self.lock, self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO mail_items VALUES (?,?,?,?,?,?)",
                (
                    key,
                    self.fingerprint(result["email"]),
                    now,
                    result["status"],
                    1,
                    json.dumps(result, ensure_ascii=False),
                ),
            )
        return self.find(result["email"])

    def get(self, key):
        with self.lock:
            row = self.db.execute(
                "SELECT * FROM mail_items WHERE id=?", (key,)
            ).fetchone()
        if not row:
            raise KeyError(key)
        return {
            **json.loads(row["payload"]),
            "id": key,
            "created_at": row["created_at"],
            "status": row["status"],
            "version": row["version"],
        }

    def list(self):
        with self.lock:
            keys = [
                row[0]
                for row in self.db.execute(
                    "SELECT id FROM mail_items ORDER BY created_at DESC"
                )
            ]
        return [self.get(key) for key in keys]

    def review(self, key, action, reviewer, draft, expected_version):
        with self.lock, self.db:
            item = self.get(key)
            if (
                item["status"] != "awaiting_review"
                or item["version"] != expected_version
            ):
                raise ReviewConflict("该任务状态已变化，请刷新；审核不能重复提交。")
            if action == "approve" and (not draft.strip() or len(draft) > 3000):
                raise ValueError("通过审核需要1至3000字符的草稿。")
            status = "approved" if action == "approve" else "rejected"
            event = {
                "action": action,
                "reviewer": reviewer,
                "original_draft": item["draft"],
                "edited_draft": draft,
                "previous_version": item["version"],
            }
            self.db.execute(
                "INSERT INTO review_events VALUES (?,?,?,?)",
                (
                    uuid.uuid4().hex,
                    key,
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(event, ensure_ascii=False),
                ),
            )
            item.update(draft=draft, reviewed_by=reviewer)
            self.db.execute(
                "UPDATE mail_items SET status=?, version=version+1, payload=? WHERE id=?",
                (status, json.dumps(item, ensure_ascii=False), key),
            )
        return self.get(key)

    def audit(self, key):
        self.get(key)
        with self.lock:
            return [
                {"created_at": row[0], **json.loads(row[1])}
                for row in self.db.execute(
                    "SELECT created_at,payload FROM review_events WHERE item_id=? ORDER BY created_at",
                    (key,),
                )
            ]
