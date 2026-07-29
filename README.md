# 招聘评估工作流

> 简历评估工作流：飞书多维表管职位 + Moka 抓简历库（带面试标签）+ 8 维框架评估 + 评估结果回写飞书。
> 代码与数据分离：代码在本目录（`D:\projects\hajifeng-scvsystem`，GitHub `hajifeng2/hajifeng-scvsystem`），数据（简历/评估产出）在 OneDrive，`config.json` 的 paths 用绝对路径连接。换机器只改 `config.json`。

## 这是什么

一套把**职位信息、简历库、评估打分**串起来的工作流：

1. 职位信息写进飞书多维表「职位表」
2. 读职位表，本地建三区工作区（简历库 / 待评估 / 评估完成）
3. 简历库 = Moka 批量抓的该职位候选人（带面试结论标签）；待评估 = 手动上传的外渠道简历
4. 对简历库 + 职位信息做群体分析，用 Moka 面试结论当真实标签，形成「评估参考」
5. 拿职位信息 + 简历库校准，评估待评估简历，写备注（单人评估卡），搬进评估完成区，结果回写飞书「评估结果表」

设计细节见 [docs/工作流总览.md](docs/工作流总览.md)。AI 工作规范见 [CLAUDE.md](CLAUDE.md)。

## 三系统分工

| 系统 | 角色 | 在本文件夹里的形态 |
|---|---|---|
| 飞书多维表 | 职位权威源 + 评估结果聚合视图 | 通过 lark-cli 读写（scripts/） |
| Moka 自动化 | 简历库批量获取（带面试标签） | `moka/` 分支：本文件夹内抓取（需 Edge + Moka 登录） |
| 简历筛选框架 | 8 维评估 + 群体分析方法论 + PDF 提取规范 | 复制进 docs/ + templates/ |

## 前置依赖

| 依赖 | 说明 | 安装 |
|---|---|---|
| Python 3.14 + pymupdf | PDF 文本提取（唯一指定工具） | `pip install pymupdf` |
| lark-cli | 飞书多维表读写 | `npm i -g @larksuite/cli` |
| 飞书 user 身份 | 文档所有者，免协作者免审 | `lark-cli auth login`（浏览器 OAuth） |
| Moka 简历目录 | 简历库的输入（PDF + JSON） | 用 Moka 系统下载，见下 |

## Moka 简历抓取（`moka/` 可选子流程）

> **可选**。主流程（评估）只要求简历库有数据，不关心数据怎么来。`moka/` 是填简历库的方式之一。

简历库三种填法，任选其一：

| 填法 | 何时用 | 成本 |
|---|---|---|
| ① 跑 `moka/` 子流程抓（本节） | 没有现成数据、要自包含 | 需 Edge + Moka 登录 |
| ② `config.moka_resumes_root` 指向已有数据（如 `D:/摩卡系统/resumes`） | 已有 Moka 下载、零成本复用 | 改一行 config |
| ③ 手工放 PDF+JSON 到 `moka_output/<职位>/<阶段>/` | 临时/少量 | 手动 |

**方式①：`moka/` 子流程**，产出到 in-folder `moka_output/`：

```
moka_output/<职位>/<阶段>/<序号>_<姓名>.pdf + <序号>_<姓名>.json
```

JSON 里 `conclusions[].result`（通过/待定/淘汰）是面试阶段的评估校准标签。

**前置**（一次性，见 [moka/README.md](moka/README.md)）：
1. `cd moka && npm install`（装 playwright-core，不下载浏览器）
2. 双击 `moka/start-edge-debug.bat` 启动 CDP Edge（9222 端口）
3. 首次在该 Edge 的 `.edge-auto` profile 里登录 `app.mokahr.com`，保持登录

**抓取**：`node moka/moka-fetch.js "职位名" ["阶段名"]`（阶段默认「面试」，6 阶段见 `moka/stages.json`）

> Edge + Moka 登录是物理依赖，换机器要重做一次登录。脚本/配置都跟文件夹走。
> 抓取脚本基于 Moka 系统的 `moka-dl-with-interview.js` 改写（stage 参数化 + in-folder 输出）。

## 快速上手

```bash
# 1. 装依赖
pip install pymupdf                # PDF 提取（Python 侧）
cd moka && npm install && cd ..    # Moka 抓取（Node 侧，playwright-core）

# 2. 登录飞书（已登录跳过）
lark-cli auth login

# 3. 复制配置并按实际填
cp config.example.json config.json
#   编辑 config.json：feishu token/table_id、moka_job_map（飞书职位名->Moka目录名）
#   paths.workspace_root / moka_resumes_root 填数据目录绝对路径（本机指 OneDrive:\简历管理系统Onedrive\工作区 和 \resumes）

# 4. 一次性建两张评估表（评估结果表 + moka简历库表），把返回的两个 table_id 回写 config.json
cd scripts
python setup_eval_table.py

# 5. [可选] Moka 抓简历库。若已有 Moka 数据（如 D:\摩卡系统\resumes），
#    改 config.json 的 moka_resumes_root 指向它即可跳过本步
node ../moka/moka-fetch.js "客户端开发（U3D）"          # 需先启动 CDP Edge + 登录 Moka

# 6. 对每个职位跑评估流程（见 scripts/README.md）
python step1_write_job.py 职位字段.json        # 写职位到飞书
python step2_setup_workspace.py "职位名"         # 读职位 + 建三区
python step3_copy_moka_library.py "职位名"       # 复制 Moka 简历库 + 标签
#   手动把外渠道简历 PDF 放进 工作区/<职位>/待评估/
python step4_extract_pdf.py "工作区/<职位>/简历库"  # 提 txt
python step4_extract_pdf.py "工作区/<职位>/待评估"
#   Agent 在对话中做评估（读 txt2 -> 8 维打分 -> 评估卡），详见 CLAUDE.md / docs/评估框架
python step5_write_eval_result.py 评估结果.json   # 每份评估写飞书
```

## 文件夹结构

```
README.md                  # 本文件
CLAUDE.md                  # AI 工作规范（接手 AI 必读）
config.example.json        # 配置模板（复制为 config.json）
docs/
├── 工作流总览.md           # 五步流程完整说明
├── PDF文本提取方法.md       # pymupdf 提取规范（必守）
└── 评估框架/              # 8 维评估 + 群体分析方法论
templates/                 # 岗位画像 / 单人评估卡 / 群体报告 / 简历库标签 模板
moka/                      # Moka 抓取分支（Edge CDP + playwright-core）
│   ├── README.md          # 抓取 setup + 用法 + 阶段表 + 标签局限
│   ├── moka-fetch.js      # 主抓取
│   ├── moka-retry-failed.js
│   ├── moka-backfill-json.js
│   ├── stages.json
│   ├── start-edge-debug.bat
│   └── package.json
scripts/                   # 机械活脚本（评估打分由 Agent 在对话中做）
│   ├── README.md          # 脚本运行顺序 + 脚本/Agent 分工
│   ├── setup_eval_table.py
│   ├── step1_write_job.py
│   ├── step2_setup_workspace.py
│   ├── step3_copy_moka_library.py
│   ├── step4_extract_pdf.py
│   ├── step5_write_eval_result.py
│   └── lib/               # config / lark_base / moka_label / pdf_extract
└── 工作区/                 # 实际评估工作区（按职位分；本机在 OneDrive，不在代码目录）
```

## 红线

- 不删/改名任何 PDF 原件（文件名编码了求职意向）
- PDF 提取**只用 pymupdf**（step4），不用其它工具直读 PDF 做评估输入
- 候选人隐私（电话/邮箱）脱敏，不外发、不用于分析以外
- Moka 简历库标签只在面试结论提交后有意义，面试没面完别评估
- 飞书表结构变更（建表/改字段）属 schema 变更，先确认
