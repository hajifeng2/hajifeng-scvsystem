# 脚本使用说明

> 脚本只做**机械活**（飞书读写、PDF 提取、Moka 复制、建目录）。
> **评估打分是 Agent 在对话中做的**（读 txt2/ -> 按 docs/评估框架 打分 -> 写评估卡 md），不写代码。

## 前置

1. `pip install pymupdf`（PDF 提取）
2. `lark-cli auth login`（飞书 user 身份登录，见 ../README.md）
3. 复制 `../config.example.json` 为 `../config.json`，按实际填：
   - `feishu.app_token` / `职位表_table_id`
   - `paths.moka_resumes_root`（Moka 的 resumes 根目录）
   - `moka_job_map`（飞书职位名 -> Moka 目录名）
   - `ocr.tesseract_exe` / `ocr.tessdata_dir`（Tesseract OCR 路径，换机器只改这；仅 `ocr_pdf.py` 用，不用 OCR 可不填）
4. 跑一次 `python setup_eval_table.py` 建两张评估表（评估结果表 + moka简历库表），把返回的两个 table_id 回写 config.json

## 每个职位跑一次的流程

| 顺序 | 脚本 / 动作 | 干啥 | 谁干 |
|---|---|---|---|
| 0 | `setup_eval_table.py` | 建两张评估表（一次性） | 脚本 |
| 1 | `step1_write_job.py 职位字段.json` | 写职位到飞书职位表 | Agent 定字段 + 脚本写 |
| 2 | `step2_setup_workspace.py "职位名"` | 读职位 + 建三区目录 | 脚本建目录，Agent 据打印的字段写岗位画像 |
| 3 | `step3_copy_moka_library.py "职位名"` | 复制 Moka 简历库 + 生成标签清单（**前置：简历库源已填**，见下） | 脚本 |
| — | 手动 | 把外渠道简历 PDF 放进 `工作区/<职位>/待评估/` | 你 |
| 4a | `step4_extract_pdf.py "工作区/<职位>/简历库"` | 简历库 PDF 提 txt | 脚本 |
| 4b | `step4_extract_pdf.py "工作区/<职位>/待评估"` | 待评估 PDF 提 txt | 脚本 |
| 4c | Agent | 读简历库 txt2 -> 8 维评估 -> 单人评估卡；用 Moka 标签做群体分析 -> 评估参考 md | Agent |
| 4d | `step5_write_eval_result.py 简历库评估结果.json`（每份） | 简历库评估写飞书 **moka简历库表**（来源=简历库，带 Moka 标签） | 脚本 |
| 5a | Agent | 读待评估 txt2 -> 8 维评估 + 评估参考校准 -> 单人评估卡（备注） | Agent |
| 5b | — | 把待评估 PDF + 评估卡搬进 `评估完成/<verdict>/` | Agent |
| 5c | `step5_write_eval_result.py 待评估评估结果.json`（每份） | 待评估评估写飞书 **评估结果表**（来源=待评估） | 脚本 |

## 注意

- **PDF 提取只用 step4（pymupdf）**，不要用 Read 工具直读 PDF 做评估输入（水印处理不一致，见 docs/PDF文本提取方法.md）
- **简历库标签时效**：Moka 面试结论提交后才有意义。面试没面完就跑，标签大片「未面」。刷新 = 重抓 Moka + 重跑 step3
- **简历库源（step3 前置，三选一）**：
  - ① 跑 `moka/` 可选子流程：`node moka/moka-fetch.js "职位" ["阶段"]` 抓到 `moka_output/<职位>/<阶段>/`（需 CDP Edge + Moka 登录，见 `moka/README.md`）。补跑失败用 `moka/moka-retry-failed.js`，补 JSON 用 `moka/moka-backfill-json.js`
  - ② `config.moka_resumes_root` 指向已有 Moka 数据（如 `D:/摩卡系统/resumes`），零成本复用
  - ③ 手工放 PDF+JSON 到 `moka_output/<职位>/<阶段>/`
  - step3 只认 `moka_resumes_root` 指向的目录里有 PDF+JSON，不关心是谁放的
- **select 字段值**：写职位表前先确认合法选项（step1 文档里有一行命令查 field-list）
- 评估卡放哪：简历库的评估卡放 `工作区/<职位>/简历库/<姓名>.md`；待评估的放 `评估完成/<verdict>/<姓名>.md`（与 PDF 同名）
