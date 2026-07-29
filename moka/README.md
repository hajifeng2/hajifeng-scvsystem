# Moka 简历抓取（可选子流程）

> **可选**。主流程（评估）只要求简历库有数据。本子流程是填简历库的方式①（从 Moka 抓）。
> 另两种：② config 指向已有 Moka 数据；③ 手工放 PDF+JSON。详见上级 README。
> 从 Moka 批量抓某职位某阶段的简历 PDF + JSON（面试阶段含面试结论标签）。
> 通过 Edge CDP 连本机已登录的 Edge，**不下载浏览器**（用 playwright-core）。

## 前置（一次性）

1. **装依赖**：`cd moka && npm install`（装 playwright-core，不下载浏览器）
2. **启动 CDP Edge**：双击 `start-edge-debug.bat`
   - 首次：Edge 会用本文件夹下 `.edge-auto` 这个独立 profile 打开（空 profile）
   - 在该 Edge 里登录 `app.mokahr.com`（游族 Moka），保持登录
   - 之后复用该 profile，不用重复登录
   - 若你已有登录好的 profile（如 `D:\摩卡系统\.edge-auto`），改 `start-edge-debug.bat` 里的 `PROFILE=` 指向它
3. **验证端口**：`curl -s http://localhost:9222/json/version` 有响应即可

> Edge 136+ 阻止 `--remote-debugging-port` 在默认 profile 上工作，故用独立 `.edge-auto` profile。
> 抓取脚本用 `connectOverCDP('http://localhost:9222')` 连上 Edge，不断开它。

## 用法

```bash
# 抓某职位某阶段（阶段名见 stages.json，默认「面试」）
node moka-fetch.js "客户端开发（U3D）"              # 默认面试阶段
node moka-fetch.js "客户端开发（U3D）" "初筛"        # 抓初筛阶段
node moka-fetch.js "运营实习生" "沟通offer"

# 补跑下载失败的 PDF（扫所有职位的该阶段 download-record.json）
node moka-retry-failed.js                # 默认面试
node moka-retry-failed.js "初筛"

# 给已有 PDF 补面试 JSON（PDF 在但 JSON 缺/旧）
node moka-backfill-json.js "游戏测试实习生" "系统策划实习生"   # 默认面试阶段
```

## 产出

```
moka_output/<职位>/<阶段>/<序号>_<姓名>.pdf + <序号>_<姓名>.json + download-record.json
```

- 序号 = search-candidate 返回位置（稳定索引 `i+1`），不用「目录文件数+1」（失败/重跑会错位）
- 断点续传：已存在的 PDF 跳过，JSON 仍重生成
- 面试阶段 JSON 含 `conclusions[].result`（通过/待定/淘汰）= 评估校准标签

## 阶段表（stages.json，pipelineId=72655 游族校招）

| stageId | 阶段 | stageId | 阶段 |
|---|---|---|---|
| 3670 | 初筛 | 3672 | 面试 |
| 3671 | 用人部门筛选 | 3673 | 沟通offer |
| 99209 | 笔试/测评 | 3674 | 待入职 |

内置阶段（已入职/已归档）无 stageId，不在表内。换流水线改 `stages.json` 的 `pipelineId` + `stages`。

## 标签局限（重要）

- **面试结论标签（通过/待定/淘汰）只有面试阶段确定有**。`conclusions` 来自 search-candidate 的 `interviewRecords`，其它阶段若候选人有面试记录也会带上（ bonus），但不保证。
- `feedbacks`（面试官评语）普遍未填（游族这批只填结论），不可强求。
- 抓非面试阶段 = 主要拿 PDF；校准仍以**面试阶段**抓的为准。

## 已知限制

- **非面试阶段的详情页 URL 是推测的**（面试用 `/interviews` 路径已验证；其它阶段用 `/application/{id}` 通用路径）。若非面试阶段下载失败，可能需调 `moka-fetch.js` 里的 `detailUrl`。
- 下载按钮约 5-10% 概率「no download」，用 `moka-retry-failed.js` 补跑。
- `personalUrl`/`previewUrl`（OSS 直链）带签名会过期，别缓存复用；下载走 UI 点按钮最稳。
- 网络代理偶发 `ERR_PROXY_CONNECTION_FAILED`，等恢复重跑。

## 与工作流的衔接

抓取产出在 `moka_output/<职位>/<阶段>/`。`scripts/step3_copy_moka_library.py` 从这里复制进 `工作区/<职位>/简历库/`（原件不动）。
`config.json` 的 `paths.moka_resumes_root` 默认指向 in-folder `moka_output`（也可改回外部 `D:/摩卡系统/resumes`）。

## 红线

- 不删/改名 `moka_output/` 下的 PDF（命名是约定，序号是稳定索引）
- `connectOverCDP` 连常驻 Edge，**不要用 `launchPersistentContext`**（会和 CDP 抢 profile 锁）
- search-candidate 必须 `limit:200`（默认 30 只拿第一页，会漏人）
- 候选人隐私（电话/邮箱）不外发
