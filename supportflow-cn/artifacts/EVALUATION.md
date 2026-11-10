# 中文售后场景评测记录

- 执行时间（UTC）：2026-11-10T09:21:31.109697+00:00
- 模式：offline
- 场景检查通过：12/12
- 固定基准日：2026-11-10；订单、客户和运单均为虚构。
- 默认模式使用规则模拟模型，通过结果不能证明真实大模型的语义理解能力。
- 检查工具调用、业务状态与退款记录数量；不测试真实支付或真实订单系统。

| 场景 | 工具 | 状态 | 检查通过 |
|---|---|---|---|
| S01 物流查询 | track_shipment | answered | 是 |
| S02 小额退款 | check_refund_eligibility, request_refund | answered | 是 |
| S03 大额待审批 | check_refund_eligibility, request_refund | awaiting_approval | 是 |
| S04 超期拦截 | check_refund_eligibility | answered | 是 |
| S05 跨客户订单 | check_refund_eligibility | answered | 是 |
| S06 取消未发货 | cancel_order | answered | 是 |
| S07 拒绝取消已发货 | cancel_order | answered | 是 |
| S08 政策检索 | search_policies | answered | 是 |
| S09 人工交接 | escalate_to_human | answered | 是 |
| S10 缺少订单号 | list_my_orders | answered | 是 |
| S11 超额退款 | check_refund_eligibility, request_refund | answered | 是 |
| S12 订单明细 | get_order | answered | 是 |
