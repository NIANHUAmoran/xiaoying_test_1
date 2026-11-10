# 需求与验收

用户是内容团队。目标是找出待处理素材，形成无冲突、可确认的发布排期建议，保存草稿并准确报告状态。本项目对应第 1 题“素材审核与发布排期 Agent”，需求及验收范围在本文件完整列明。

## 功能与边界

输入请求 ID、素材 ID、发布时间及其硬性程度；本地数据提供素材元信息、审核规则、已有占用快照和候选时段。四个工具分别读取素材、检查规则、查询时段和保存草稿。每项输出审核状态、风险原因、缺失字段、原要求、建议时间、待确认项、保存状态和草稿 ID。

模型决定下一动作，观察工具结果后再次决策。模型不能授权发布时间变更，不能编造保存成功，不能调用发布功能。缺失信息返回待补充，风险阻断，冲突时查询候选，硬性时间变更保持待确认。无可用时段时请求用户确认新的范围。

## 成功标准

- 六项必验场景都有成组输入、实际输出和独立 Trace，全部记录在 `examples/` 并由评估文档引用。
- 正常素材可生成草稿；缺少信息或触发风险时不违规写入；硬性时间冲突只生成待确认建议；保存失败明确返回失败。
- 同一请求重复提交后仍只有一份同 ID 草稿，排期变化时能重新检查并更新建议；执行上限有效且返回未完成状态。
- 至少两条真实模型路径显示模型根据工具结果调整参数、动作或结束，记录工具参数、返回结果、后续动作及简要依据。
- 评审可从 README 复制命令复现离线样例和测试；界面、部署、多 Agent 与真实发布均不在本题实现范围内。

## 验收映射

| 原题要求 | 实现 | 验证 |
| --- | --- | --- |
| 正常排期 | 审核通过、查询、事务保存 | `test_normal_persists_confirmed_draft_and_never_publishes` |
| 素材信息缺失 | 必填字段检查，停止写入 | `test_missing_metadata_stops_without_writes` |
| 规则风险 | 违规标签阻断，写入前再次检查审核结果 | `test_risk_blocks_saving`、`test_model_cannot_bypass_risk_gate` |
| 时间冲突 | 查询候选、硬约束待确认 | `test_conflict_keeps_original_time_and_requires_confirmation` |
| 重复提交 | 请求约束校验、唯一键、同草稿更新 | `test_duplicate_survives_reopen_and_creates_one_draft` |
| 保存失败 | 异常返回与事务回滚，不能报成功 | `test_save_failure_is_not_reported_as_success`、`test_sqlite_write_error_rolls_back_and_is_reported` |
| 占用变化 | 快照替换、重查、保存前事务复核 | `test_changed_occupancy_updates_same_draft_not_original_requirement`、`test_race_after_query_is_rechecked_at_save` |
| 确认边界 | 仅输入 approved_slot 可新增同意 | `test_user_can_confirm_existing_draft_without_creating_another` |
| 有界执行 | 每项最多指定决策步数 | `test_step_limit_returns_incomplete` |
| 真实模型动态决策 | HTTP 适配器逐步接收观察、返回动作 | `live-normal.output.json`、`live-conflict.output.json`、`live-missing.output.json`；真实模型根据不同观察选择保存、待确认或停止 |

## 显式假设

- 时区在输入中明确指定，输出规范为 UTC+08:00；样例使用固定日期而不依赖运行当天。
- 一个时段代表单渠道一个不可重叠的发布位置，不处理视频时长或时间区间交叉。
- 所有草稿预留候选时段，包括待确认草稿；这只是避免建议冲突，不能视为修改用户硬性要求。
- `data/world.json` 的 occupied_slots 是本次启动的完整外部排期快照，会替换旧外部快照；已持久化草稿仍参与占用检查。
- 请求文件是可信用户输入；素材及元数据是不可信内容。CLI 没有多用户身份认证。
- `approved_slot` 是对同一请求追加的确认事件；其他原始内容变更须创建新请求。确认不意味着发布，已确认授权暂不支持撤回。
- Mock 是显式离线固定策略，不是模型，不能满足真实 ReAct 效果证明。
