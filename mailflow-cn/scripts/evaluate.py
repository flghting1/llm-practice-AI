# ruff: noqa: E402 -- standalone source-checkout launcher
"""Evaluate explicitly labelled synthetic cases; no external service by default."""

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dotenv import load_dotenv

from mailflow_cn.flow import EmailInput, MailWorkflow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="offline", choices=["offline", "openai"])
    parser.add_argument("--output-dir", default="artifacts")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    flow = MailWorkflow(args.provider)
    results = []
    for case in json.loads(
        (ROOT / "data/mailflow_evaluation.json").read_text(encoding="utf-8")
    ):
        item = flow.process(
            EmailInput(**{key: case[key] for key in ["sender", "subject", "body"]})
        )
        results.append(
            dict(
                id=case["id"],
                name=case["name"],
                expected=case["expected_route"],
                actual=item["decision"]["route"],
                matched=item["decision"]["route"] == case["expected_route"],
                status=item["status"],
                elapsed_ms=item["elapsed_ms"],
                error=item["error"],
            )
        )
    passed = sum(row["matched"] for row in results)
    report = dict(
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=args.provider,
        python=platform.python_version(),
        dataset="30 manually-labelled synthetic development cases; not a holdout benchmark",
        total=len(results),
        route_matches=passed,
        route_match_rate=passed / len(results),
        external_model_verified=args.provider != "offline",
        results=results,
    )
    target = ROOT / args.output_dir
    target.mkdir(parents=True, exist_ok=True)
    (target / "evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    rows = [
        "# 邮件场景评测记录",
        "",
        f"- 执行时间（UTC）：{report['generated_at']}",
        f"- 模式：{args.provider}",
        f"- 路由匹配：{passed}/{len(results)}",
        "- 数据：人工编写的合成开发用例，非真实客户邮件，非独立留出测试集。",
        "- 离线耗时只反映规则和本地流程，不能代表大模型响应速度。",
        "- 测试不衡量真实投递率，也未调用邮箱发送接口。",
        "",
        "| 用例 | 预期 | 实际 | 匹配 |",
        "|---|---|---|---|",
    ]
    rows += [
        f"| {row['id']} {row['name']} | {row['expected']} | {row['actual']} | {'是' if row['matched'] else '否'} |"
        for row in results
    ]
    rows += [
        "",
        "## 已知限制",
        "",
        "关键词规则会误判同时包含业务词和通知词的邮件，例如库存告警和订单日报。该结果保留在报告中；接入真实模型后需重新评测，不能将离线匹配率作为大模型准确率。",
        "",
    ]
    (target / "EVALUATION.md").write_text("\n".join(rows), encoding="utf-8")
    print(
        f"{args.provider}: route matches {passed}/{len(results)}; results saved to {target}"
    )


if __name__ == "__main__":
    main()
