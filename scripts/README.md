# 浏览器验收

先安装任一子项目的requirements-demo.txt，再安装 `scripts/requirements-ui.txt`。执行 `python scripts/verify_ui.py`，脚本为两个应用建立新的临时演示状态，启动8111/8112端口，完成交互后结束测试服务并保存截图与JSON记录。

Windows默认使用已安装的Edge；可通过BROWSER_EXECUTABLE指定浏览器路径。其他系统可先执行 `python -m playwright install chromium`。截图不是静态设计稿，来自实际运行页面。测试未连接真实模型或真实支付系统。
