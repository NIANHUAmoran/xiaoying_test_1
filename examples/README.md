# 验证材料索引

每个场景提供同名前缀的 `.input.json`、`.output.json`、`.trace.json`。输出是程序实际执行的完整 JSON，独立 Trace 从该输出逐项提取，保留步骤、工具参数、返回内容、下一动作和简要决策依据。独立 Trace 不重写或补造模型动作。

## 六项必验场景

| 场景 | 输入 | 实际输出 | 运行记录 |
| --- | --- | --- | --- |
| 正常排期 | [normal.input.json](normal.input.json) | [normal.output.json](normal.output.json) | [normal.trace.json](normal.trace.json) |
| 信息缺失 | [missing.input.json](missing.input.json) | [missing.output.json](missing.output.json) | [missing.trace.json](missing.trace.json) |
| 规则风险 | [risk.input.json](risk.input.json) | [risk.output.json](risk.output.json) | [risk.trace.json](risk.trace.json) |
| 时段冲突 | [conflict.input.json](conflict.input.json) | [conflict.output.json](conflict.output.json) | [conflict.trace.json](conflict.trace.json) |
| 重复提交 | [duplicate.input.json](duplicate.input.json) | [duplicate.output.json](duplicate.output.json) | [duplicate.trace.json](duplicate.trace.json) |
| 工具保存失败 | [save-failure.input.json](save-failure.input.json) | [save-failure.output.json](save-failure.output.json) | [save-failure.trace.json](save-failure.trace.json) |

这六组为显式离线 Mock，证明业务流程和规则，不证明真实模型决策质量。公共合成数据为 [world.json](../data/world.json)；保存失败使用 [save-failure.world.json](../data/save-failure.world.json)。重复场景先执行 normal，再在同一数据库提交相同请求，实际草稿数量检查见 [run-summary.json](run-summary.json)。

## 真实模型路径

| 场景 | 输入 | 实际输出 | 运行记录 |
| --- | --- | --- | --- |
| 正常 | [live-normal.input.json](live-normal.input.json) | [live-normal.output.json](live-normal.output.json) | [live-normal.trace.json](live-normal.trace.json) |
| 冲突 | [live-conflict.input.json](live-conflict.input.json) | [live-conflict.output.json](live-conflict.output.json) | [live-conflict.trace.json](live-conflict.trace.json) |
| 信息缺失 | [live-missing.input.json](live-missing.input.json) | [live-missing.output.json](live-missing.output.json) | [live-missing.trace.json](live-missing.trace.json) |

这三组由配置的 `qwen3.8-max` 实际运行生成，标记为 `mode=live`。数据库历史核对结果在 [live-validation-summary.json](live-validation-summary.json)。模型观察到可用、冲突和缺字段时，分别保存原定时间、保存待确认替代建议、停止并请求补充。

## 扩展与失败记录

`confirm`、`changed-occupancy`、`race` 各自也有同名输入、输出、Trace：分别验证用户明确确认、占用变化后重新提交、查询后时段被占。changed-occupancy 的输出包含 before/after 两次真实离线执行，复现脚本在两次执行间注入 19:00 占用。

`live-conflict-before-fix` 三个文件保留提示词修正前的真实未完成路径。`live-config-check.json` 是隔离全部模型配置后的负例检查，验证程序不会自动转用 Mock，不表示当前模型不可用。

## 复现与评审

在项目根目录执行 `python tests/reproduce.py`，重建离线输出、提取全部 Trace 并运行测试；执行 `python tests/check_submission.py`，核对交付结构、场景覆盖和输入/输出/Trace 对应关系。原始真实模型输出在离线复现中保持不变。

测试结果见 [test-results.txt](test-results.txt)，交付核查见 [submission-check.json](submission-check.json)，预期、实际结果及限制见 [评估文档](../docs/03-evaluation.md)。
