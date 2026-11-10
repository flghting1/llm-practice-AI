"""Chinese support workbench: local demo API and a same-origin web UI."""

from __future__ import annotations

import os
import threading
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from support_agent.api import create_app
from support_agent.chinese import ChineseSupportModel
from support_agent.models import get_model
from support_agent.persistence import PersistentStore
from support_agent.policy import PolicyConfig
from support_agent.service import SupportService

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class ChineseSupportService(SupportService):
    def _run(self, graph_input, customer_id, thread_id):
        result = super()._run(graph_input, customer_id, thread_id)
        if result.status == "awaiting_approval":
            result.reply = f"订单 {result.approval['order_id']} 申请退款 ¥{result.approval['amount']}，超过自动处理阈值，已进入人工审批队列。尚未记录模拟退款。"
        return result


def make_console(data_path: Path | None = None):
    state_dir = data_path or Path(os.getenv("APP_DATA_DIR", str(ROOT / "var")))
    state_dir.mkdir(parents=True, exist_ok=True)
    db = str(state_dir / "support.sqlite3")
    store = PersistentStore.load(ROOT / "data/cn/store.json")
    store.enable_persistence(db)
    provider = os.getenv("SUPPORT_MODEL_PROVIDER", "offline").lower()
    model = ChineseSupportModel() if provider == "offline" else get_model(provider)
    service = ChineseSupportService(
        model=model,
        store=store,
        data_dir=ROOT / "data/cn",
        policy=PolicyConfig(approval_threshold=Decimal("200")),
        db_path=db,
    )
    app = create_app(service)
    app.title = "SupportFlow CN · 中文售后工作台"
    lock = threading.RLock()
    app.state.service = service
    app.state.provider = provider

    # A single local worker serializes graph mutations; business uniqueness is also enforced by SQLite.
    original_chat, original_resolve = service.chat, service.resolve_approval

    def locked_chat(*args, **kwargs):
        with lock:
            return original_chat(*args, **kwargs)

    def locked_resolve(*args, **kwargs):
        with lock:
            return original_resolve(*args, **kwargs)

    service.chat, service.resolve_approval = locked_chat, locked_resolve

    @app.get("/demo/info")
    def info():
        return {
            "mode": provider,
            "simulated_payments": True,
            "demo_date": str(store.today),
            "customers": store.customers,
            "approval_threshold": 200,
            "return_window_days": 30,
        }

    @app.get("/demo/orders/{customer_id}")
    def orders(customer_id: str):
        if customer_id not in store.customers:
            raise HTTPException(404, "演示客户不存在")
        return [
            {**asdict(order), "total": str(order.total), "refunded": str(order.refunded)}
            for order in store.orders_for(customer_id)
        ]

    @app.get("/demo/summary")
    def summary():
        return {
            "pending": len(service.pending_approvals()),
            "refunds": len(store.refunds),
            "tickets": len(store.tickets),
            "mode": provider,
        }

    @app.get("/")
    def index():
        return FileResponse(ROOT / "web/index.html")

    app.mount("/assets", StaticFiles(directory=ROOT / "web"), name="assets")
    return app


app = make_console()
