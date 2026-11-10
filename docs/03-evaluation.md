# 实际验证与限制

验证环境：Windows、Python 3.12.3。执行 `python tests/reproduce.py` 可复现离线场景并运行测试，完整实际结果见 [test-results.txt](../examples/test-results.txt)。当前测试 **31 项通过、0 失败、0 错误**。另外已通过配置的 `qwen3.8-max` 接口运行三条真实模型路径。单元测试中的 HTTP 替身与这些真实网络运行是不同的证据来源。

整理为独立 `xiaoying_test_1` 交付目录后，已从该目录重新执行离线示例复现和全部 31 项测试，结果通过。代码、测试与合成资料不依赖外层项目；交付中保留原始真实模型运行记录，目录整理阶段没有再次调用模型服务。真实配置文件与本地运行数据库未纳入交付。

## 交付结构与证据对应

项目根目录按规范保留 README、src、tests、examples、data、docs、依赖声明、配置模板及 Git 忽略规则；docs 中为五份指定文档。复现及核对脚本放在 tests，合成资料和故障规则放在 data。`python tests/check_submission.py` 核对结构、链接和全部证据的对应关系，实际结果见 [submission-check.json](../examples/submission-check.json)。

| 六项验收 | 输入 | 实际输出 | 独立运行记录 |
| --- | --- | --- | --- |
| 正常排期 | [normal.input.json](../examples/normal.input.json) | [normal.output.json](../examples/normal.output.json) | [normal.trace.json](../examples/normal.trace.json) |
| 信息不足 | [missing.input.json](../examples/missing.input.json) | [missing.output.json](../examples/missing.output.json) | [missing.trace.json](../examples/missing.trace.json) |
| 规则风险 | [risk.input.json](../examples/risk.input.json) | [risk.output.json](../examples/risk.output.json) | [risk.trace.json](../examples/risk.trace.json) |
| 时段冲突 | [conflict.input.json](../examples/conflict.input.json) | [conflict.output.json](../examples/conflict.output.json) | [conflict.trace.json](../examples/conflict.trace.json) |
| 重复提交 | [duplicate.input.json](../examples/duplicate.input.json) | [duplicate.output.json](../examples/duplicate.output.json) | [duplicate.trace.json](../examples/duplicate.trace.json) |
| 工具失败 | [save-failure.input.json](../examples/save-failure.input.json) | [save-failure.output.json](../examples/save-failure.output.json) | [save-failure.trace.json](../examples/save-failure.trace.json) |

独立 Trace 直接从实际输出中的 trace 提取，未重新生成决策；交付核查逐项比较两者一致性。正常、信息不足、工具失败三组满足最低材料覆盖，另外三组补齐本题全部必验点。

## 预期与实际结果

| 场景 | 预期 | 本次实际结果及文件 |
| --- | --- | --- |
| 正常 | 审核通过，保存草稿 | `draft_saved/saved`；[normal.output.json](../examples/normal.output.json) |
| 元数据缺失 | 待补 owner，不保存 | `needs_information/not_attempted`；[missing.output.json](../examples/missing.output.json) |
| 版权风险 | 阻断，不保存 | `blocked/not_attempted`；[risk.output.json](../examples/risk.output.json) |
| 18:00 被占 | 建议 19:00，保留 18:00，待确认 | `needs_confirmation/saved`；[conflict.output.json](../examples/conflict.output.json) |
| 用户确认 19:00 | 同草稿转为确认状态，仍未发布 | `draft_saved`，同 draft_id；[confirm.output.json](../examples/confirm.output.json) |
| 重复提交 | 一份草稿、同 ID | `duplicate=true`，数据库数量为 1；[duplicate.output.json](../examples/duplicate.output.json)、[run-summary.json](../examples/run-summary.json) |
| 保存工具失败 | 明确失败，不伪造成功 | `failed/failed`、`storage_unavailable`、无 draft_id；[save-failure.output.json](../examples/save-failure.output.json) |
| 占用变化后重提 | 建议更新至 20:00，草稿数量仍为 1 | `draft_updated=true`；[changed-occupancy.output.json](../examples/changed-occupancy.output.json) |
| 查询后被占 | 首次保存失败，重查后换时段 | `slot_conflict_at_save` 后建议 20:00 待确认；[race.output.json](../examples/race.output.json) |

以上记录全部标明 `mode=mock` 和 `decision_evidence=offline_mock_not_model_evidence`。正常路径经过审核、查询和保存；信息不足路径读取后结束；竞争路径保存失败后重查。它们证明流程、状态和业务校验行为，**不证明真实模型会作出这些选择**。

另外已验证模型越权动作和额外参数会被拒绝、模型提前结束不能冒充完成、步数上限有效、SQLite 实际写入异常回滚、两个连接争抢同一时段时只有一个成功、待确认草稿不会重复预留同一位置、旧外部占用可被新快照释放。测试中的提示注入素材只验证确定性权限边界，不声称完成真实模型提示注入鲁棒性评估。

## 真实模型验收

2026 年 11 月 11 日（Asia/Shanghai），用户配置本地 `.env` 后，真实调用 `qwen3.8-max` 完成以下场景。汇总及数据库核对结果见 [live-validation-summary.json](../examples/live-validation-summary.json)。

| 真实场景 | 模型实际动作和结果 | 证据 |
| --- | --- | --- |
| 正常 | 读取 → 审核 → 查询 → 保存 → 结束，共 5 步；19:00 可用，保存草稿，数据库一份，confirmed=true | [live-normal.output.json](../examples/live-normal.output.json) |
| 冲突 | 相同初始工具链后，观察到 18:00 被占，选择 19:00；保存后根据 confirmed=false 结束为待确认，共 5 步；原始要求仍为 18:00，数据库一份 | [live-conflict.output.json](../examples/live-conflict.output.json) |
| 信息缺失 | 读取到缺少 owner 后选择结束，共 2 步；needs_information，未写草稿，数据库数量 0 | [live-missing.output.json](../examples/live-missing.output.json) |

三条真实路径分别同时提供 [正常输入](../examples/live-normal.input.json) / [正常 Trace](../examples/live-normal.trace.json)、[冲突输入](../examples/live-conflict.input.json) / [冲突 Trace](../examples/live-conflict.trace.json)、[信息不足输入](../examples/live-missing.input.json) / [信息不足 Trace](../examples/live-missing.trace.json)。

这三条是真实模型根据不同工具返回调整参数或动作的记录，不使用离线策略。`python tests/check_live_outputs.py` 可将输出状态、动作序列、草稿 ID、原始与建议时间、确认位与实际 SQLite 数据逐项核对；历史核对结果已归档。该命令需要先在本目录生成三个对应的真实运行数据库。

真实接入曾有网络连接失败，在获得系统权限后于沙箱外调用成功。冲突路径也曾提前 finish：模型认为硬性时间不能变，所以没有提出可保存建议。程序准确报告 incomplete，未伪称保存成功；[修正前实际记录](../examples/live-conflict-before-fix.output.json) 保留。随后明确提示“保存替代建议只建立待确认草稿，不修改原要求”，重跑通过，并增加提前结束与诊断脱敏的回归测试。

本次证明配置接口可用及这三次业务决策符合预期，不代表模型未来每次都稳定成功。规则风险、重复提交、用户确认和保存失败有离线业务测试，本轮未额外进行这些场景的真实模型运行，也未进行大样本成功率、提示注入鲁棒性或延迟统计评估。[live-config-check.json](../examples/live-config-check.json) 是刻意隔离所有模型配置的负例测试，不表示当前 `.env` 未配置。

## 已知局限

- 合成规则仅检查必填字段和禁止标签，不进行视频理解、版权事实核验或真实内容安全审核。
- 单渠道固定时段互斥，不处理时长重叠、跨渠道容量、优先级或最优排期。
- 待确认草稿预留候选时段，目前没有撤销、过期释放或授权撤回命令；更大系统应补齐生命周期管理。
- 模型协议不合法会明确结束为未完成，未做自动 JSON 修复。当前输入给模型的观察不包含完整长历史，历史工具结果使用最新状态与 Trace 供复核。
- CLI 输入被视为可信用户操作，未实现多用户身份校验。补查仅限本地素材读取，无法补足数据源本来缺失的事实。
- 多素材逐项执行，不是整批全有或全无事务；某项失败时前面已保存的草稿不会撤销。
- 旧草稿在新请求因素材缺失或审核风险而停止时会保持原记录，不会自动撤销；任何后续执行都必须重新审核，且本项目没有发布入口。
- 尚未配置 GitHub 远程仓库、评审权限及最终 commit SHA，未完成远程提交。
