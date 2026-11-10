"""Verify the two local demo apps in a fresh headless Edge profile."""
import json
import atexit
import os
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

BASE = Path(__file__).resolve().parents[1]
(BASE / "work").mkdir(exist_ok=True)
errors = []
results = []
servers = []

def stop_servers():
    for process in servers:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

atexit.register(stop_servers)
for name, port in (("mailflow-cn",8111),("supportflow-cn",8112)):
    state = tempfile.mkdtemp(prefix=name+"-",dir=BASE / "work")
    environment = dict(os.environ,APP_DATA_DIR=state,LANGSMITH_TRACING="false")
    process = subprocess.Popen([sys.executable,"run.py","--mode","offline","--port",str(port)],cwd=BASE/name,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    servers.append(process)
    deadline = time.monotonic()+20
    while True:
        try:
            with urlopen(f"http://127.0.0.1:{port}/health",timeout=1) as response:
                assert response.status==200
            break
        except Exception:
            if time.monotonic()>deadline or process.poll() is not None:
                raise RuntimeError(f"{name} did not start")
            time.sleep(.2)

with sync_playwright() as playwright:
    edge = Path(os.getenv("BROWSER_EXECUTABLE", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"))
    browser = playwright.chromium.launch(executable_path=str(edge) if edge.exists() else None, headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 1080}, device_scale_factor=1)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8111", wait_until="networkidle")
    expect(page.locator("#mode")).to_have_text("离线规则演示")
    page.get_by_role("button", name="载入演示样例", exact=True).click()
    expect(page.locator("#total")).to_have_text("6")
    expect(page.get_by_role("button", name="载入演示样例", exact=True)).to_be_enabled()
    expect(page.locator("#detail")).to_contain_text("采购")
    expect(page.get_by_role("button", name="通过审核", exact=True)).to_be_visible()
    mail_shots = BASE / "mailflow-cn/docs/screenshots"
    mail_shots.mkdir(parents=True, exist_ok=True)
    expect(page.locator("#toast")).to_be_hidden(timeout=6000)
    page.screenshot(path=str(mail_shots / "workbench.png"), full_page=True)
    if page.get_by_role("button", name="通过审核", exact=True).count():
        page.locator("#draft").fill("您好，感谢咨询。请补充产品规格及交付地区，核实后将提供正式报价。")
        page.get_by_role("button", name="通过审核", exact=True).click()
    expect(page.locator("#approved")).to_have_text("1")
    expect(page.get_by_role("link", name="导出已审核草稿 ↓", exact=True)).to_be_visible()
    page.get_by_role("button", name="查看审核留痕", exact=True).click()
    expect(page.locator("#audit-content")).to_contain_text("演示审核员")
    expect(page.locator("#toast")).to_be_hidden(timeout=6000)
    page.screenshot(path=str(mail_shots / "reviewed.png"), full_page=True)
    page.get_by_role("button", name="载入演示样例", exact=True).click()
    expect(page.locator("#total")).to_have_text("6")
    expect(page.get_by_role("button", name="载入演示样例", exact=True)).to_be_enabled()
    results.append({"project":"mailflow-cn","checks":["six scenarios loaded","manual draft editing and approval","approved draft export link","review audit","duplicate examples deduplicated"],"passed":True})
    expect(page.locator("#toast")).to_be_hidden(timeout=6000)
    page.set_viewport_size({"width":390,"height":844})
    page.screenshot(path=str(mail_shots / "mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "mail mobile horizontal overflow"
    page.set_viewport_size({"width":1440,"height":1080})
    page.goto("http://127.0.0.1:8112",wait_until="networkidle")
    expect(page.locator("#mode")).to_have_text("离线规则演示")
    expect(page.locator("#orders-count")).to_have_text("5")
    page.get_by_role("button",name="大额退款审批",exact=True).click()
    page.get_by_role("button",name="发送并处理",exact=True).click()
    expect(page.locator("#pending")).to_have_text("1")
    expect(page.locator("#refunds")).to_have_text("0")
    expect(page.locator("#chat")).to_contain_text("尚未记录模拟退款")
    support_shots = BASE / "supportflow-cn/docs/screenshots"
    support_shots.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(support_shots / "approval.png"),full_page=True)
    page.get_by_role("button",name="批准模拟退款",exact=True).click()
    expect(page.locator("#refunds")).to_have_text("1")
    expect(page.locator("#pending")).to_have_text("0")
    expect(page.locator("#chat")).to_contain_text("模拟退款已记录")
    page.screenshot(path=str(support_shots / "workbench.png"),full_page=True)
    page.get_by_role("button",name="开始新会话",exact=True).click()
    page.get_by_role("button",name="超期退款拦截",exact=True).click()
    page.get_by_role("button",name="发送并处理",exact=True).click()
    expect(page.locator("#chat")).to_contain_text("不符合")
    expect(page.locator("#refunds")).to_have_text("1")
    page.locator("#customer").select_option("C200")
    expect(page.locator("#orders-count")).to_have_text("1")
    expect(page.locator("#orders")).not_to_contain_text("无线降噪耳机")
    page.set_viewport_size({"width":390,"height":844})
    page.screenshot(path=str(support_shots / "mobile.png"),full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "support mobile horizontal overflow"
    results.append({"project":"supportflow-cn","checks":["customer orders loaded","large refund pauses without payout","manual approval resumes flow","expired refund blocked","customer switch isolates orders","mobile no horizontal overflow"],"passed":True})
    assert not errors, errors
    context.close()
    browser.close()

for result in results:
    result.update(generated_at=datetime.now(timezone.utc).isoformat(),browser="headless Microsoft Edge, fresh profile",viewport="1440x1080 and 390x844",page_errors=errors)
    (BASE/result["project"]/"artifacts/ui-checks.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"results":results},ensure_ascii=False,indent=2))
