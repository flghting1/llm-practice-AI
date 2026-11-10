"""Persist demo business mutations, including refunds, across service restarts."""

from __future__ import annotations

import sqlite3
import uuid
from decimal import Decimal

from support_agent.store import Refund, Store


class PersistentStore(Store):
    def enable_persistence(self, path: str) -> None:
        self._business_db = sqlite3.connect(path, check_same_thread=False, timeout=15)
        self._business_db.execute("PRAGMA journal_mode=WAL")
        with self._business_db:
            self._business_db.execute(
                "CREATE TABLE IF NOT EXISTS cn_orders (id TEXT PRIMARY KEY, status TEXT, refunded TEXT)"
            )
            self._business_db.execute(
                "CREATE TABLE IF NOT EXISTS cn_refunds (id TEXT PRIMARY KEY, order_id TEXT UNIQUE, amount TEXT, reason TEXT, approved_by TEXT)"
            )
            self._business_db.execute(
                "CREATE TABLE IF NOT EXISTS cn_tickets (id TEXT PRIMARY KEY, customer_id TEXT, summary TEXT)"
            )
            for order in self.orders.values():
                self._business_db.execute(
                    "INSERT OR IGNORE INTO cn_orders VALUES (?,?,?)", (order.id, order.status, str(order.refunded))
                )
        for order_id, status, refunded in self._business_db.execute("SELECT * FROM cn_orders"):
            if order_id in self.orders:
                self.orders[order_id].status = status
                self.orders[order_id].refunded = Decimal(refunded)
        self.refunds = [
            Refund(rid, oid, Decimal(amount), reason, reviewer)
            for rid, oid, amount, reason, reviewer in self._business_db.execute("SELECT * FROM cn_refunds")
        ]
        self.tickets = [
            dict(id=tid, customer_id=customer, summary=summary)
            for tid, customer, summary in self._business_db.execute("SELECT * FROM cn_tickets")
        ]

    def record_refund(self, order, amount, reason, approved_by):
        with self._lock, self._business_db:
            row = self._business_db.execute("SELECT status, refunded FROM cn_orders WHERE id=?", (order.id,)).fetchone()
            if not row or Decimal(row[1]) > 0:
                raise ValueError("该订单已经退款，请勿重复操作。")
            if not amount.is_finite() or amount <= 0 or amount > order.total:
                raise ValueError("退款金额必须在实付金额范围内。")
            refund = Refund(f"R-{uuid.uuid4().hex[:8]}", order.id, amount, reason, approved_by)
            try:
                self._business_db.execute(
                    "INSERT INTO cn_refunds VALUES (?,?,?,?,?)", (refund.id, order.id, str(amount), reason, approved_by)
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("该订单已经退款，请勿重复操作。") from exc
            self._business_db.execute("UPDATE cn_orders SET refunded=? WHERE id=?", (str(amount), order.id))
        order.refunded = amount
        self.refunds.append(refund)
        return refund

    def cancel(self, order):
        with self._lock, self._business_db:
            self._business_db.execute("UPDATE cn_orders SET status='cancelled' WHERE id=?", (order.id,))
        order.status = "cancelled"

    def open_ticket(self, customer_id, summary):
        ticket = {"id": f"T-{uuid.uuid4().hex[:8]}", "customer_id": customer_id, "summary": summary}
        with self._lock, self._business_db:
            self._business_db.execute("INSERT INTO cn_tickets VALUES (?,?,?)", tuple(ticket.values()))
        self.tickets.append(ticket)
        return ticket["id"]
