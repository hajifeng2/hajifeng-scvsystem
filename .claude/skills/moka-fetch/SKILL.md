---
name: moka-fetch
description: >
  Moka 简历批量抓取子流程：通过 Edge CDP 连本机已登录的 Moka，按职位+阶段抓全员简历 PDF + JSON
  （面试阶段含面试结论标签）。在以下场景使用：用户说"抓 moka""抓简历""抓面试阶段""moka 抓取"
  "补跑 PDF""补 JSON""moka 职位状态""看 Moka 各阶段人数""moka-fetch"，或要从 Moka 批量下载
  某职位某阶段简历、补跑失败 PDF、补面试 JSON、扫描各职位阶段人数时。本 skill 是招聘评估工作流
  的可选子流程（填简历库的方式①），脚本在项目 moka/ 目录，完整规则见 moka/README.md，不在此重复。
---

# Moka 简历抓取子流程

**可选**子流程。把 Moka 某职位某阶段的全员简历（PDF + JSON）批量拉到本地，供 `step3_copy_moka_library.py` 复制进简历库。
脚本在 `D:\projects\hajifeng-scvsystem\moka\`，**本 skill 是触发器 + 关键约束清单**，脚本细节见 `moka/README.md`，不在此重复。

## 1. 前置（一次性）

1. **装依赖**：`cd D:\projects\hajifeng-scvsystem\moka && npm install`（装 playwright-core，**不下载浏览器**）
2. **启动 CDP Edge**：双击 `moka/start-edge-debug.bat`
   - 首次：用 `moka/.edge-auto` 独立 profile 打开 Edge，在该 Edge 里登录 `app.mokahr.com`（游族 Moka），保持登录
   - 之后复用该 profile，不重复登录
   - 若复用已有登录 profile（如 `D:\摩卡系统\.edge-auto`），改 `start-edge-debug.bat` 里的 `PROFILE=`
3. **验证端口**：`curl -s http://localhost:9222/json/version` 有响应即可

> Edge 136+ 阻止 `--remote-debugging-port` 在默认 profile 上工作，故用独立 `.edge-auto` profile。
> 脚本用 `connectOverCDP('http://localhost:9222')` 连常驻 Edge，**不要用 `launchPersistentContext`**（会和 CDP 抢 profile 锁）。

## 2. 四个脚本

| 脚本 | 干啥 | 命令 |
|---|---|---|
| `moka-fetch.js` | 抓某职位某阶段全员 PDF+JSON | `node moka-fetch.js "职位名" ["阶段"]`（默认面试） |
| `moka-retry-failed.js` | 补跑下载失败的 PDF | `node moka-retry-failed.js ["阶段"]`（默认面试） |
| `moka-backfill-json.js` | 给已有 PDF 补面试 JSON | `node moka-backfill-json.js "职位1" ["职位2"] ["阶段"]` |
| `moka-job-status.js` | 扫各职位各阶段人数（不下 PDF） | `node moka-job-status.js` |

阶段名见 `stages.json`（pipelineId=72655 游族校招）：初筛 / 用人部门筛选 / 笔试测评 / 面试 / 沟通offer / 待入职。

## 3. 产出

```
moka_output/<职位>/<阶段>/<序号>_<姓名>.pdf + <序号>_<姓名>.json + download-record.json
moka_output/_status/<时间戳>_job-status.json   # job-status 脚本，职位×阶段人数矩阵
```

- 序号 = search-candidate 返回位置（稳定索引 `i+1`），**不用**「目录文件数+1」（失败/重跑会错位）
- 断点续传：已存在的 PDF 跳过，JSON 仍重生成
- 面试阶段 JSON 含 `conclusions[].result`（通过/待定/淘汰）= 评估校准标签

## 4. 关键约束（红线）

- **PDF 下载走 `previewUrl` OSS 签名直链**（`page.evaluate` 用 Edge 网络 fetch），**不走 UI 点击下载**--Edge 150 后 UI 点击下载全阶段失效。代码已按此实现（`moka-fetch.js` / `moka-retry-failed.js`），勿回退到点按钮。
- **`previewUrl` 签名几小时过期**，`download-record.json` 里**不存**它；`moka-retry-failed.js` 会重新调 search-candidate 拿新 previewUrl 再下。
- **`search-candidate` 必须 `limit:200`**（默认 30 只拿第一页，会漏人）。
- **职位名精确匹配**：`moka-fetch.js` 按 `c.jobTitle === JOB` 过滤，传入的职位名必须与 Moka 线上 `jobTitle` 完全一致（含全角括号），否则 0 匹配。
- **职位名以 Moka 线上为准**：`config.moka_job_map` 是带时间戳快照（`moka_job_map_updated_at`），日常可以 map 为准，但可能与线上有差距；不自动刷新，由 Agent 提醒、用户决定何时从线上重新拉取更新。
- **面试结论标签只有面试阶段确定有**：`conclusions` 来自 search-candidate 的 `interviewRecords`，其它阶段若候选人有面试记录也会带上（bonus）但不保证。抓非面试阶段 = 主要拿 PDF；校准仍以**面试阶段**抓的为准。
- **`connectOverCDP` 连常驻 Edge**，不要用 `launchPersistentContext`。
- **不删/改名 `moka_output/` 下的 PDF**（命名是约定，序号是稳定索引）。
- 候选人隐私（电话/邮箱）不外发。

## 5. 常见问题

- **0 匹配**：职位名与 Moka 线上不一致（括号/全半角）。跑 `moka-job-status.js` 看线上实际 jobTitle，或让用户从线上刷新 `moka_job_map`（更新 `moka_job_map_updated_at`）。
- **PDF 下载失败**：跑 `moka-retry-failed.js`（重新拿 previewUrl）。仍失败多为 previewUrl 过期或网络代理 `ERR_PROXY_CONNECTION_FAILED`，等恢复重跑。
- **JSON 缺/旧**：跑 `moka-backfill-json.js`（面试阶段专用，抓 interviewCard + feedbacks）。
- **想看线上各职位阶段人数**：跑 `moka-job-status.js`（以 `moka_job_map` 为统计范围，打印职位×阶段矩阵 + 存 JSON）。

## 6. 与工作流衔接

抓取产出在 `moka_output/<职位>/<阶段>/`。`scripts/step3_copy_moka_library.py` 从这里复制进 `工作区/<职位>/简历库/`（原件不动）。
`config.json` 的 `paths.moka_resumes_root` 默认指向 in-folder `moka_output`（也可改回外部 `D:/摩卡系统/resumes`）。

## 7. 配套 skill

- 评估主流程：`/resume-eval`（本 skill 是其第 3 步"三区就位"填简历库的方式①，可选）
- 飞书读写：`/feishu`
