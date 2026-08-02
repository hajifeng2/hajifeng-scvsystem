---
name: resume-eval
description: >
  招聘评估工作流入口：根据飞书职位信息 + Moka 简历库（带面试结论标签）评估外渠道简历。
  在以下场景使用：用户说"评估简历""简历评估""招聘评估""跑简历筛选""评估待评估区"
  "按职位评估简历""评估这批简历""resume-eval"，或要从飞书职位表拉职位、用 Moka 简历库
  校准、对待评估简历打分写备注时。本 skill 是 招聘评估工作流/ 文件夹的入口触发器，
  完整规则在该文件夹的 CLAUDE.md 与 docs/，不在此重复。
---

# 招聘评估工作流入口

本 skill 是 `D:\projects\hajifeng-scvsystem` 的**入口触发器**。完整规则在文件夹的 CLAUDE.md 和 docs/，**不在此重复**--先读它们。

## 1. 必读文件（权威规则，本 skill 只是入口）

- `CLAUDE.md` -- AI 工作规范、红线、脚本/Agent 分工、环境架构
- `docs/工作流总览.md` -- 五步流程细则
- `scripts/README.md` -- 脚本运行顺序

## 2. 工作流概要

5 步（详见文件夹文档）：
1. **职位入表**：Agent 把职位描述映射到飞书职位表字段 -> `step1_write_job.py` 写飞书
2. **读表建区**：`step2_setup_workspace.py "职位名"` 读职位 + 建三区 -> Agent 派生 `岗位画像_<职位>.md`
3. **三区就位**：简历库源填好（三选一：`/moka-fetch` skill 抓 / config 指向已有数据 / 手工放）-> `step3_copy_moka_library.py` 复制进简历库；待评估手动放 PDF
4. **简历库 -> 评估参考**：`step4_extract_pdf.py` 提 txt -> Agent 按 `docs/评估框架` 8 维评估 + 用 Moka 标签做群体分析 -> `评估参考_<职位>_<日期>.md` -> `step5_write_eval_result.py`（来源=简历库）写飞书
5. **待评估 -> 评估完成**：提 txt -> Agent 8 维 + 评估参考校准 -> 单人评估卡（备注）-> 搬进 `评估完成/<verdict>/` -> `step5`（来源=待评估）写飞书

**脚本干机械活（飞书读写 / PDF 提取 / Moka 复制 / 建目录），Agent 干评估打分（读 txt2/，按 docs/评估框架 8 维打分，不写代码）。**

## 3. 关键红线（易踩，务必守）

- **PDF 提取只用 `step4_extract_pdf.py`（pymupdf）**，Agent 读 `txt2/` 不读 PDF（水印处理见 `docs/PDF文本提取方法.md`）
- **Moka 标签（通过/淘汰/待定）只有面试阶段有**，面试没面完别评估
- 不删/改名 PDF 原件；简历库是复制不是移动
- 岗位画像不进飞书，本地派生；职位表 schema 不动
- 飞书写操作（建表/写记录）先跟用户确认
- 候选人隐私（电话/邮箱）脱敏，不外发

## 4. 启动流程

1. 问用户：要评估哪个职位？（要飞书职位名，如「客户端实习生（U3D）」）
2. 检查前置就绪：`config.json` 存在、飞书已登录（`lark-cli auth status`）、两张评估表已建（`feishu.评估结果表_table_id` + `feishu.moka简历库表_table_id` 都非空）、简历库源已填。没就绪则**提示用户**--装依赖（`pip install pymupdf` / `cd moka && npm install`）、建表（`setup_eval_table.py` 建两张）这些留给用户在生产环节决定，别自作主张跑
3. 按五步流程跑，每步分清脚本/Agent 职责
4. 评估时严格按 `docs/评估框架/02-评估框架.md` 8 维 + 红旗，**每分附原文证据**，不臆造；打分后写「综合评估」段（论述合不合适/为什么/关键判断/短板/验证点，是评估卡第一节，非条目罗列--读者看完即懂结论怎么来的）
5. 简历库评估用 Moka 面试结论当真实标签做群体分析（`docs/评估框架/03-群体分析方法论.md`）；待评估评估用评估参考校准

## 5. 配套 skill

- Moka 简历抓取：`/moka-fetch`（第 3 步"三区就位"填简历库的方式①，可选）
- 飞书读写：`/feishu`（lark-cli 操作多维表/记录）
- 需求/方案拷问：`/grill-me`
