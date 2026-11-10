"""Chinese demo model. Rules simulate language understanding; real tools enforce policy."""

from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from support_agent.offline_model import OfflineSupportModel, _call, _is_json


def intent_cn(text: str) -> str | None:
    if any(word in text for word in ("人工", "投诉", "经理", "客服人员")):
        return "human"
    if any(word in text for word in ("政策", "规则", "退货期限", "几天", "保修")) and not re.search(r"\d{4}", text):
        return "policy"
    for intent, words in (
        ("cancel", ("取消", "不买了")),
        ("refund", ("退货", "退款", "坏了", "破损", "退钱", "质量问题")),
        ("track", ("物流", "快递", "到哪", "发货", "配送", "什么时候到", "运单")),
        ("orders", ("我的订单", "订单列表", "买过什么")),
    ):
        if any(word in text for word in words):
            return intent
    return None


def reply_cn(results: dict, intent: str | None) -> str:
    if any("error" in value for value in results.values()):
        return "没有查到属于当前客户的这笔订单，请核对订单号。"
    if refund := results.get("request_refund"):
        if refund["status"] == "refunded":
            return f"模拟退款已记录：订单 {refund['order_id']}，金额 ¥{refund['amount']}，凭证 {refund['refund_id']}。本演示不调用支付系统。"
        if refund["status"] == "denied":
            return f"审核未通过：{refund['note']}。未执行模拟退款。"
        return f"无法退款：{reason_cn(refund.get('reason', '请联系人工核实'))}"
    if eligibility := results.get("check_refund_eligibility"):
        if not eligibility["eligible"]:
            return f"订单 {eligibility['order_id']} 不符合演示售后规则：{reason_cn(eligibility['reason'])}"
    if cancel := results.get("cancel_order"):
        if cancel["status"] == "cancelled":
            return f"订单 {cancel['order_id']}（{cancel['item']}）已在模拟订单库中取消。"
        return "当前订单已经发货或完成，不能直接取消；请按退货流程处理。"
    if track := results.get("track_shipment"):
        if track["status"] == "shipped":
            return f"订单 {track['order_id']}（{track['item']}）运输中，运单 {track['tracking']}，预计 {track['eta']} 送达。"
        if track["status"] == "delivered":
            return f"订单 {track['order_id']}（{track['item']}）已于 {track['delivered']} 签收。"
        return f"订单 {track['order_id']} 当前为待发货状态。"
    if order := results.get("get_order"):
        return f"订单 {order['order_id']}：{order['item']}，实付 ¥{order['total']}，状态 {order['status']}。"
    if orders := results.get("list_my_orders"):
        listing = "；".join(f"{order['order_id']} {order['item']}" for order in orders["orders"])
        return f"当前客户的订单：{listing}。" + ("请补充要处理的订单号。" if intent != "orders" else "")
    if policy := results.get("search_policies"):
        return (
            "\n".join(f"【{p['section']}】{p['text']}" for p in policy["results"]) or "未检索到相关规则，请转人工核实。"
        )
    if escalation := results.get("escalate_to_human"):
        return f"已生成模拟人工工单 {escalation['ticket_id']}，客服可以根据交接摘要继续处理。"
    return "请补充订单号和需要处理的问题。"


def reason_cn(reason: str) -> str:
    if "already refunded" in reason:
        return "该订单已经退款，不能重复操作。"
    if "return window" in reason:
        return "该订单已超过演示配置的30天退货期限。"
    if "hasn't been delivered" in reason:
        return "订单尚未签收，需要先核实配送状态。"
    if "most that can be refunded" in reason:
        return "申请金额超过订单可退款金额。"
    if "Cancelled orders" in reason:
        return "订单已取消，请勿重复申请退款。"
    return reason


class ChineseSupportModel(OfflineSupportModel):
    """The English path remains available for upstream regression tests."""

    @property
    def _llm_type(self) -> str:
        return "offline-chinese-support-model"

    def _respond(self, messages):
        last = max(i for i, message in enumerate(messages) if isinstance(message, HumanMessage))
        text = str(messages[last].content)
        if not re.search(r"[\u4e00-\u9fff]", text):
            return super()._respond(messages)
        results = {
            message.name: json.loads(message.content)
            for message in messages[last + 1 :]
            if isinstance(message, ToolMessage) and _is_json(message.content)
        }
        intent = intent_cn(text)
        order_match = re.search(r"(?<!\d)(\d{4})(?!\d)", text)
        order_id = order_match.group(1) if order_match else None
        if not results:
            if intent is None and order_id is None:
                return AIMessage(content="我可以协助查询订单、物流、退款和取消订单。请补充订单号和具体问题。")
            return self._first_step(intent, order_id, text)
        eligibility = results.get("check_refund_eligibility")
        if eligibility and eligibility.get("eligible") and "request_refund" not in results:
            amount = re.search(r"(?:退(?:款)?|金额)\s*(\d+(?:\.\d{1,2})?)\s*元|[¥￥]\s*(\d+(?:\.\d{1,2})?)", text)
            requested = (amount.group(1) or amount.group(2)) if amount else eligibility["max_amount"]
            return _call("request_refund", order_id=eligibility["order_id"], amount=float(requested), reason=text[:200])
        return AIMessage(content=reply_cn(results, intent))
