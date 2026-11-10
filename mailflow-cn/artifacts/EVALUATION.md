# 邮件场景评测记录

- 执行时间（UTC）：2026-11-10T09:21:27.280821+00:00
- 模式：offline
- 路由匹配：28/30
- 数据：人工编写的合成开发用例，非真实客户邮件，非独立留出测试集。
- 离线耗时只反映规则和本地流程，不能代表大模型响应速度。
- 测试不衡量真实投递率，也未调用邮箱发送接口。

| 用例 | 预期 | 实际 | 匹配 |
|---|---|---|---|
| M01 询价 | respond | respond | 是 |
| M02 库存 | respond | respond | 是 |
| M03 产品资料 | respond | respond | 是 |
| M04 批量订购 | respond | respond | 是 |
| M05 合作需求 | respond | respond | 是 |
| M06 退款咨询 | respond | respond | 是 |
| M07 物流催问 | respond | respond | 是 |
| M08 破损投诉 | respond | respond | 是 |
| M09 退货材料 | respond | respond | 是 |
| M10 会议通知 | notify | notify | 是 |
| M11 仓库公告 | notify | notify | 是 |
| M12 周报 | notify | notify | 是 |
| M13 抄送 | notify | notify | 是 |
| M14 会议纪要 | notify | notify | 是 |
| M15 广告 | ignore | ignore | 是 |
| M16 促销 | ignore | ignore | 是 |
| M17 中奖 | ignore | ignore | 是 |
| M18 推广 | ignore | ignore | 是 |
| M19 账号变更 | review | review | 是 |
| M20 验证码 | review | review | 是 |
| M21 绕过审核 | review | review | 是 |
| M22 英文注入 | review | review | 是 |
| M23 密码 | review | review | 是 |
| M24 含糊请求 | review | review | 是 |
| M25 空泛问候 | review | review | 是 |
| M26 附件缺失 | review | review | 是 |
| M27 营销中夹带指令 | review | review | 是 |
| M28 报价未确认 | respond | respond | 是 |
| M29 库存通知歧义 | notify | respond | 否 |
| M30 订单日报歧义 | notify | respond | 否 |

## 已知限制

关键词规则会误判同时包含业务词和通知词的邮件，例如库存告警和订单日报。该结果保留在报告中；接入真实模型后需重新评测，不能将离线匹配率作为大模型准确率。
