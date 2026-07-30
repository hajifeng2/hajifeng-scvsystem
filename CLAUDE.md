# 招聘评估工作流 - AI 工作规范

> 接手 AI 必读本文件 + [docs/工作流总览.md](docs/工作流总览.md) + [scripts/README.md](scripts/README.md)。
> 代码与数据分离：代码在本目录（`D:\projects\hajifeng-scvsystem`），数据在 OneDrive，`config.json` 的 paths 用绝对路径连接。换机器只改 `config.json`。

## 项目定位

把飞书多维表（职位 + 评估结果）、Moka 简历库（带面试标签）、8 维评估框架串成一个端到端招聘评估工作流。

## 环境架构（代码与数据分离）

- **代码主环境**：本目录 `D:\projects\hajifeng-scvsystem`（`.git` + GitHub `hajifeng2/hajifeng-scvsystem`）。代码改动 + git 操作都在这。
- **数据**：OneDrive `简历管理系统Onedrive\` 的 `工作区/`、`moka_output/`、`resumes/`，多设备同步；`config.json` 的 paths 用绝对路径指向它（`lib/config.py:resolve()` 支持绝对路径，无需改脚本）。
- **评估时数据路径**：Agent 对话中读写工作区（读 `txt2/`、写评估卡）以 `config.json` 的 `paths.workspace_root`（OneDrive 绝对路径）为根；D 盘 `工作区/` 只是 `.gitkeep` 占位，真实数据在 OneDrive。脚本用 `resolve()` 已处理，Agent 评估同理。
- ⚠️ **OneDrive 是纯数据目录**（只含 `工作区/`、`moka_output/`、`resumes/`，无代码无 `.git`）；代码/git 操作只在 D 盘。`moka/*.js`、`_gen_labels.py` 用相对 `moka_output` 路径，D 盘找不到，需抓 Moka 时单独处理。

## 脚本 vs Agent 分工（核心）

| 谁 | 干啥 |
|---|---|
| **脚本**（scripts/） | 机械活：飞书读写、PDF 提 txt、Moka 复制、建目录。不思考。 |
| **Agent**（对话中） | 评估打分：读 txt2/ -> 按 docs/评估框架 8 维打分 -> 写评估卡 md -> 群体分析。不写代码。 |

**别用 Read 工具直读 PDF 做评估输入**--必须先跑 `step4_extract_pdf.py` 提 txt2/，Agent 读 txt2/。水印处理见 [docs/PDF文本提取方法.md](docs/PDF文本提取方法.md)。

## 五步流程（详见 docs/工作流总览.md）

1. **职位入表**：Agent 把职位描述映射到职位表 15 字段 -> `step1_write_job.py` 写飞书 -> 拿 record_id
2. **读表建区**：`step2_setup_workspace.py "职位名"` 读职位 + 建三区（简历库/待评估/评估完成/{被接收,未通过,待定}）-> Agent 据打印字段派生 `岗位画像_<职位>.md`
3. **三区就位**：简历库源填好（可选子流程 `moka/moka-fetch.js` 抓 / config 指向已有数据 / 手工放）-> `step3_copy_moka_library.py` 复制进简历库；待评估手动放 PDF
4. **简历库 -> 评估参考**：`step4_extract_pdf.py` 提 txt -> Agent 8 维评估 + 用 Moka 标签做群体分析 -> `评估参考_<职位>_<日期>.md` -> `step5_write_eval_result.py`（来源=简历库）写飞书
5. **待评估 -> 评估完成**：提 txt -> Agent 8 维 + 评估参考校准 -> 单人评估卡（备注）-> 搬进 `评估完成/<verdict>/` -> `step5`（来源=待评估）写飞书

## 关键约束（红线）

- **PDF 提取只用 pymupdf**（step4 / docs/PDF文本提取方法.md），Agent 读 txt2/ 不读 PDF
- **Moka 标签时效**：`conclusions[].result`（通过/待定/淘汰）只在面试结论提交后有意义；面试没面完别评估
- **不删/改名 PDF 原件**；简历库是**复制**不是移动
- **画像不进多维表**：岗位画像在本地从职位表行派生（JD + 关注点 + 排除项 + 毕业时间 + 时长要求），职位表 schema 不动
- **隐私脱敏**：电话/邮箱存档案时脱敏（`138****1234`），不外发
- **结论附原文证据**：所有打分引用简历原文，不臆造（见 docs/评估框架/02-评估框架.md）
- **飞书 schema 变更**（建表/改字段）先确认；user 身份操作，不动 bot

## 评估方法（复用，不另造）

- 单人评估：[docs/评估框架/02-评估框架.md](docs/评估框架/02-评估框架.md) 的 8 维度 + 红旗 + 拒因，基准 = 本地 `岗位画像_<职位>.md`
- 群体分析：[docs/评估框架/03-群体分析方法论.md](docs/评估框架/03-群体分析方法论.md) 五步，用 Moka 面试结论当真实标签（不是 Agent 自评）
- 产出：[templates/单人评估卡模板.md](templates/单人评估卡模板.md) + [templates/群体分析报告模板.md](templates/群体分析报告模板.md)
- 数据规范：[docs/评估框架/01-数据规范.md](docs/评估框架/01-数据规范.md)（Candidate Schema、清洗、脱敏）

## 飞书两张评估表（新建）

`setup_eval_table.py` 一次性建两张，所属职位 link 关联职位表：

- **评估结果表**（待评估）：姓名 / 所属职位 / 评级(A\|B\|C+\|C) / 评估结论(被接收\|未通过\|待定) / 评估日期 / 评估卡路径
- **moka简历库表**（简历库）：评估结果表字段 + `Moka面试结论`(通过\|待定\|淘汰\|未面) / `评估卡内容`（文字摘要）/ `核心原因总结`（一句话合适/不合适原因）。校准对比「Agent verdict vs Moka 实际」

`step5` 按来源分派：来源=简历库 -> moka简历库表；来源=待评估 -> 评估结果表。两个 table_id 都回写 config.json。与本地三区 1:1 对应（简历库区↔moka简历库表，评估完成区↔评估结果表）。

## 配置

`config.json`（从 `config.example.json` 复制）：
- `feishu.app_token` / `职位表_table_id` / `评估结果表_table_id`（建表后回写）/ `identity`
- `paths.moka_resumes_root`：Moka 的 resumes 根目录（本机填 OneDrive 绝对路径）
- `paths.workspace_root`：评估工作区根（本机填 OneDrive 绝对路径；`lib/config.py` 的 `resolve()` 支持相对/绝对）
- `moka_job_map`：飞书职位名 -> Moka 目录名（Step3 定位 Moka 简历用）

## 不在本文件夹内的事

- 飞书 OAuth 登录（环境前提）
- Edge + Moka 登录（`moka/` 抓取的环境前提，换机器重做一次）
- 实际评估打分（Agent 在对话中按 docs/评估框架 执行）

Moka 抓取**在**本文件夹内（`moka/` 分支：`moka-fetch.js` + `moka-retry-failed.js` + `moka-backfill-json.js`），不再依赖外部 Moka 系统。抓取需 Edge CDP（端口 9222）+ Moka 登录，详见 `moka/README.md`。

## 已知集成点（待用户处理）

- **Moka职位名 ↔ 飞书职位名 ↔ 本地文件夹名** 三方映射：现 `moka_job_map` 只覆盖飞书↔Moka；本地工作区文件夹名用飞书职位名（去斜杠）。若要对接 `D:\职位简历\职位同步映射.md` 的 record_id 体系，后续整合。
- 飞书多维表 token：本文件夹默认 `<app_token>...`；`D:\职位简历\CLAUDE.md` 记的是 `<旧token>...`（旧）。统一时改 config.json。
