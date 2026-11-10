"""The local-only Chinese mail review workbench."""

import json
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from mailflow_cn.flow import EmailInput, MailWorkflow
from mailflow_cn.storage import Repository, ReviewConflict

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class ReviewInput(BaseModel):
    action: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=80)
    draft: str = Field(max_length=3000)
    expected_version: int = Field(ge=1)


def create_app(data_dir=None, workflow=None):
    path = Path(data_dir or os.getenv("APP_DATA_DIR", str(ROOT / "var")))
    path.mkdir(parents=True, exist_ok=True)
    repo = Repository(path / "mailflow.sqlite3")
    flow = workflow or MailWorkflow(os.getenv("MAIL_MODEL_PROVIDER", "offline"))
    app = FastAPI(title="MailFlow CN · 邮件协作工作台", version="1.0.0")
    app.state.repo, app.state.workflow = repo, flow

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": flow.provider, "delivery_enabled": False}

    @app.get("/api/examples")
    def examples():
        return json.loads(
            (ROOT / "data/mailflow_examples.json").read_text(encoding="utf-8")
        )

    @app.get("/api/items")
    def items():
        return repo.list()

    @app.get("/api/summary")
    def summary():
        items = repo.list()
        return {
            "total": len(items),
            "pending": sum(item["status"] == "awaiting_review" for item in items),
            "attention": sum(item["status"] == "needs_attention" for item in items),
            "approved": sum(item["status"] == "approved" for item in items),
            "mode": flow.provider,
        }

    @app.post("/api/items")
    def process(email: EmailInput):
        existing = repo.find(email.model_dump())
        if existing:
            return {**existing, "duplicate": True}
        return {**repo.add(flow.process(email)), "duplicate": False}

    @app.post("/api/items/{key}/review")
    def review(key: str, decision: ReviewInput):
        try:
            return repo.review(key, **decision.model_dump())
        except KeyError as exc:
            raise HTTPException(404, "邮件任务不存在") from exc
        except ReviewConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/items/{key}/audit")
    def audit(key: str):
        try:
            return repo.audit(key)
        except KeyError as exc:
            raise HTTPException(404, "邮件任务不存在") from exc

    @app.get("/api/items/{key}/export")
    def export(key: str):
        try:
            item = repo.get(key)
        except KeyError as exc:
            raise HTTPException(404, "邮件任务不存在") from exc
        if item["status"] != "approved":
            raise HTTPException(409, "只有已通过人工审核的草稿可以导出。")
        text = f"To: {item['email']['sender']}\nSubject: Re: {item['email']['subject']}\n\n{item['draft']}\n\n[人工审核后的演示草稿，未实际发送]"
        return Response(
            text,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="reply-{key[:8]}.txt"'
            },
        )

    @app.get("/")
    def index():
        return FileResponse(ROOT / "web/index.html")

    app.mount("/assets", StaticFiles(directory=ROOT / "web"), name="assets")
    return app


app = create_app()
