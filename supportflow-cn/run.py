# ruff: noqa: E402 -- standalone source-checkout launcher
"""Start the local portfolio workbench without installing upstream tutorial extras."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
parser = argparse.ArgumentParser()
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", default=8102, type=int)
parser.add_argument("--mode", choices=["offline", "openai"])
args = parser.parse_args()
if args.mode:
    os.environ["SUPPORT_MODEL_PROVIDER"] = args.mode
os.environ.setdefault("SUPPORT_MODEL_PROVIDER", "offline")
os.environ.setdefault("LANGSMITH_TRACING", "false")
import uvicorn

uvicorn.run("support_agent.console:app", host=args.host, port=args.port)
