# 第 1 题：素材审核与发布排期 Agent

本目录是第 1 题的独立项目根目录。先进入 `xiaoying_test_1`，再执行下文命令；GitHub 交付时以本目录内容作为仓库根目录。

为内容团队审核素材、查询冲突时段并保存排期草稿。输出包含审核状态、风险原因、建议时段、待确认项与实际保存结果。**只保存草稿，不提供真实发布功能。**

已实现真实模型决策循环和独立离线 Mock，使用 Python 标准库与 SQLite，无第三方依赖。31 项测试通过，六类验收场景均有输入、实际输出和独立 Trace；已使用配置的 `qwen3.8-max` 完成正常、冲突、信息缺失三条真实模型路径，并核对 SQLite 草稿与输出一致。详见 [验证材料索引](examples/README.md) 和 [真实验证汇总](examples/live-validation-summary.json)。

## 项目目录

```text
xiaoying_test_1/
├── README.md                     # 环境、安装、运行、评审入口与提交信息
├── requirements.txt              # Python 版本与依赖说明
├── .env.example                  # 模型配置模板，无真实密钥
├── .gitignore
├── src/                          # 项目代码与模型、工具接入
├── tests/                        # 可执行测试、示例复现与交付核查脚本
├── data/                         # 合成素材、审核规则、排期与故障数据
├── examples/                     # 输入、实际输出、Trace、测试结果
│   ├── README.md                 # 场景与验证材料索引
│   ├── normal.input.json
│   ├── normal.output.json
│   ├── normal.trace.json
│   ├── missing.input.json        # 信息不足场景
│   ├── missing.output.json
│   ├── missing.trace.json
│   ├── save-failure.input.json   # 工具失败场景
│   ├── save-failure.output.json
│   ├── save-failure.trace.json
│   ├── live-*.{input,output,trace}.json
│   └── test-results.txt
└── docs/
    ├── 01-requirements.md        # 用户、目标、范围、成功标准
    ├── 02-solution.md            # 调用流程、动态决策、技术取舍
    ├── 03-evaluation.md          # 测试预期、实际结果、失败与限制
    ├── 04-ai-usage.md            # AI 辅助、个人贡献与验证
    └── 05-retrospective.md       # 最难问题、学习收获、下一步
```

## 快速运行

环境：Python 3.12+；已在 Windows / Python 3.12.3 验证。在项目根目录执行：

```powershell
python --version
python tests/reproduce.py
python tests/check_submission.py
```

无须 `pip install`。第一条脚本在临时数据库中复现全部离线场景并执行测试；第二条检查目录、五份指定文档、每组输入/输出/Trace、真实路径及测试结果是否齐全。分别生成 [测试结果](examples/test-results.txt) 与 [交付核查结果](examples/submission-check.json)。

单独运行程序或测试：

```powershell
python -m src --mock --input examples/normal.input.json --db .runtime/demo.sqlite3 --output .runtime/normal.output.json
python -B -m unittest discover -s tests -v
```

SQLite 数据库与输出目录会自动创建。重复提交同一请求、同一素材只保留一份草稿；已有其他请求的草稿会影响可用时段。需要隔离实验时，使用新的 `--db` 路径。

## 模型接口配置

在项目根目录创建 `.env`，参照 [.env.example](.env.example) 填入：

```dotenv
LLM_BASE_URL=https://你的服务商接口前缀/v1
LLM_MODEL=服务商提供的准确模型ID
LLM_API_KEY=在本地填写密钥
```

程序自动读取根目录 `.env`，也可用 `--env-file 路径` 指定文件。当前进程的同名环境变量优先；修改文件后请启动新的程序进程。支持 `KEY=VALUE`、整行注释、单引号或双引号包裹的单行值；不支持变量展开、多行密钥和行尾注释。`.env` 已加入 `.gitignore`，配置值不会进入模型提示词或普通运行日志。

交付目录提供 `.env.example`。真实运行时在本目录自行创建 `.env`，或使用 `--env-file` 显式指定本机配置文件。已归档的真实运行记录可直接阅读，离线测试无需配置模型。

`LLM_BASE_URL` 是接口前缀，程序自动追加 `/chat/completions`，因此不要把这一段重复写入前缀。服务须支持 HTTPS、Bearer 认证、`model/messages/temperature` 请求字段，以及 `choices[0].message.content` 返回格式。模型须按提示返回纯 JSON 动作；不支持只有其他协议的接口。具体地址、模型 ID 和访问权限应以所选服务商配置为准。

配置后可执行以下命令，复现真实模型路径：

```powershell
python -m src --input examples/normal.input.json --db .runtime/live-normal.sqlite3 --output examples/live-normal.output.json
python -m src --input examples/conflict.input.json --db .runtime/live-conflict.sqlite3 --output examples/live-conflict.output.json
python -m src --input examples/missing.input.json --db .runtime/live-missing.sqlite3 --output examples/live-missing.output.json
```

本次实际正常路径为 5 步并保存已确认时间的草稿；冲突路径为 5 步，保留 18:00 原要求、建议 19:00 并保存待确认草稿；信息缺失路径为 2 步，读取后立即结束并请求补充 owner。运行后可用 `python tests/check_live_outputs.py` 核对这三条输出与本地数据库，再运行 `python tests/reproduce.py` 提取新的独立 Trace。上述数据库核对依赖本地 `.runtime` 数据库，新的评审环境应先运行三条真实命令；归档 JSON 可直接阅读。

此时不要加 `--mock`。缺配置会报错退出，不会悄悄切换离线模式。每次模型请求超时 30 秒，每项素材默认至多 12 个决策步骤，包含 `finish`；可设置 `--max-steps 1..100`。达到上限或模型返回非法动作时，结果为 `incomplete`，已保存草稿的事实仍会保留。真实接入曾发现提示词对待确认草稿的语义不明确，已修正；[修正前记录](examples/live-conflict-before-fix.output.json) 保留用于说明失败与改进。

## 冲突与用户确认

下面的样例要求 18:00，但该时段被占用，离线策略会建议 19:00，保存为待确认草稿；原始 18:00 要求保持不变：

```powershell
python -m src --mock --input examples/conflict.input.json --db .runtime/confirmation.sqlite3
python -m src --mock --input examples/confirm.input.json --db .runtime/confirmation.sqlite3
```

第二条输入由用户明确增加 `approved_slot`，确认替代时间；使用同一请求 ID 更新原草稿，不新增第二份。真实模式下删除 `--mock` 即可。`approved_slot` 必须来自可信请求输入，素材内容和模型参数不能赋予用户同意。已确认的同一时间授权会保留，不能通过省略字段悄悄撤回。

输入 `items` 可包含多项素材。每项的字段为：

| 字段 | 含义 |
| --- | --- |
| `material_id` | 合成数据中的素材 ID，在请求内唯一 |
| `requested_slot` | 带日期和时区偏移的 ISO 时间，输出统一为 UTC+08:00 |
| `hard_time` | 默认 `true`；为 `false` 时允许工具确认可用的替代时间 |
| `approved_slot` | 可选，由用户明确同意的替代时段；可在同一请求上追加确认 |

`request_id` 必填。同一请求的原始内容不可修改，`approved_slot` 作为确认事件除外；修改素材、原定时间或其他条件请使用新的请求 ID。重复提交会复核当前素材和占用情况，必要时更新原草稿的建议，草稿 ID 与数量保持稳定。

## 复现验收材料

```powershell
python tests/reproduce.py
```

该命令在临时数据库中运行真实 CLI，重建离线示例、核对退出码及重复保存的草稿数量，并运行测试，将报告写入 `examples/test-results.txt`。它不会调用真实模型，也不修改日常使用的 `.runtime` 数据库。重新执行会更新示例运行时间。

| 验收点 | 实际输出/记录 |
| --- | --- |
| 正常排期 | [normal.output.json](examples/normal.output.json) |
| 信息缺失 | [missing.output.json](examples/missing.output.json) |
| 规则风险 | [risk.output.json](examples/risk.output.json) |
| 时段冲突 | [conflict.output.json](examples/conflict.output.json) |
| 重复提交 | [duplicate.output.json](examples/duplicate.output.json)、[run-summary.json](examples/run-summary.json) |
| 保存失败 | [save-failure.output.json](examples/save-failure.output.json) |
| 用户确认 | [confirm.output.json](examples/confirm.output.json) |
| 占用变化与保存时竞争 | [changed-occupancy.output.json](examples/changed-occupancy.output.json)、[race.output.json](examples/race.output.json) |

保存失败可单独复现：

```powershell
python -m src --mock --input examples/save-failure.input.json --data data/save-failure.world.json --db .runtime/failure.sqlite3
```

退出码：`0` 表示本轮正常结束（含待确认、待补充、规则阻断）；`1` 表示某项失败或未完成；`2` 表示输入、配置或初始化错误。业务是否成功须查看每项状态，不能仅用退出码判断。

## 结构与评审入口

- `src/agent.py`：模型动作循环、步数限制与最终状态生成。
- `src/models.py`：真实 HTTP 模型适配器与显式离线策略。
- `src/tools.py`、`src/store.py`：四类业务工具、事务复核与幂等保存。
- `tests/`：业务边界、对抗输入、并发保存和配置加载测试。
- `data/`：合成素材、规则和排期快照；`examples/`：输入、实际输出、Trace 和测试报告。
- [需求](docs/01-requirements.md)、[方案](docs/02-solution.md)、[评估与局限](docs/03-evaluation.md)、[AI 使用说明](docs/04-ai-usage.md)、[复盘](docs/05-retrospective.md)。

当前假设为单发布渠道、固定时间点互斥。包括待确认建议在内的草稿都会预留候选时段，以避免批量建议冲突；预留不代表用户已授权替代时间。尚未实现时长重叠、多渠道、草稿撤销或授权撤回；详见评估文档。GitHub 仓库、评审权限与最终 commit SHA 尚未配置，本地材料不等于已完成远程提交。

## 提交信息

| 项目 | 内容 |
| --- | --- |
| 题号 | 1：素材审核与发布排期 Agent |
| GitHub URL | 创建仓库后填写 |
| 最终 commit SHA | 完成最终提交后填写 |
| 私有仓库权限 | 提交前向指定评审账号授予读取权限 |

提交前补充本人实际投入、独立修改与复核记录，详见 [AI 使用说明](docs/04-ai-usage.md) 和 [复盘](docs/05-retrospective.md)。
