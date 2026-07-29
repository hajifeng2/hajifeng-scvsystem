// Moka 各职位状态扫描：遍历所有阶段，统计每个职位各阶段当前人数（不下载 PDF）
// 用法: node moka-job-status.js
// 产出: ../moka_output/_status/<时间戳>_job-status.json + 控制台打印职位×阶段矩阵
// 前提: Edge CDP 端口 9222 已启动且已登录 Moka（见 start-edge-debug.bat）
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const sleep = ms => new Promise(r => setTimeout(r, ms));

const stages = JSON.parse(fs.readFileSync(path.join(__dirname, 'stages.json'), 'utf8'));
const PIPELINE_ID = stages.pipelineId;
const config = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config.json'), 'utf8'));
// 职位列表 = moka_job_map 的值去重（Moka 侧职位名）
const JOBS = [...new Set(Object.values(config.moka_job_map))];
const STAGE_NAMES = Object.keys(stages.stages);

const BASE = path.join(__dirname, '..', 'moka_output');
const outDir = path.join(BASE, '_status');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const ctx = browser.contexts()[0];
  const p = await ctx.newPage();

  // 用首个阶段列表页建立登录上下文
  const firstStageId = stages.stages[STAGE_NAMES[0]];
  const LIST_URL = `https://app.mokahr.com/candidates?pipelineId=${PIPELINE_ID}&stageId=${firstStageId}&jobPreference=assist&jobStatus%5B0%5D=open`;
  console.log('建立登录上下文...');
  await p.goto(LIST_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(3000);

  const now = new Date();
  const result = { time: now.toISOString(), pipelineId: PIPELINE_ID, jobs: JOBS, stages: STAGE_NAMES, matrix: {} };
  // matrix[job][stage] = { count, total, truncated }

  for (const stageName of STAGE_NAMES) {
    const stageId = stages.stages[stageName];
    const searchBody = { pipelineId: PIPELINE_ID, stageId, jobPreference: 'assist', jobStatus: ['open'], jobIds: [], enableAiFilter: false, onlyHmAssignment: false, limit: 200 };
    let resp;
    try {
      resp = await p.evaluate(async (body) => {
        const r = await fetch('https://app.mokahr.com/api/outer/ats-candidate-search-left/candidate/search-candidate/v2', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
        });
        return await r.json();
      }, searchBody);
    } catch (e) {
      console.error(`❌ [${stageName}] 请求失败: ${e.message}`);
      for (const job of JOBS) {
        if (!result.matrix[job]) result.matrix[job] = {};
        result.matrix[job][stageName] = { count: null, total: null, truncated: false, error: e.message };
      }
      continue;
    }
    const apps = resp?.data?.applications || [];
    const total = resp?.data?.total ?? apps.length;
    const truncated = total > apps.length;

    // 按职位分组（只统计我们关心的职位）
    const byJob = {};
    for (const c of apps) {
      if (JOBS.includes(c.jobTitle)) byJob[c.jobTitle] = (byJob[c.jobTitle] || 0) + 1;
    }
    console.log(`\n[${stageName}] (stageId=${stageId}) API返回 ${apps.length} 条, total=${total}${truncated ? ' ⚠️截断' : ''}`);
    for (const job of JOBS) {
      const count = byJob[job] || 0;
      if (!result.matrix[job]) result.matrix[job] = {};
      result.matrix[job][stageName] = { count, total, truncated };
      if (count > 0) console.log(`  ${job}: ${count}`);
    }
  }

  await browser.close();

  // 写 JSON
  const ts = now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const jsonPath = path.join(outDir, `${ts}_job-status.json`);
  fs.writeFileSync(jsonPath, JSON.stringify(result, null, 2), 'utf8');

  // 打印矩阵
  console.log('\n\n========== 各职位状态矩阵（open 候选人数）==========');
  const colW = 10;
  const header = '职位'.padEnd(22) + STAGE_NAMES.map(s => s.padEnd(colW)).join('') + '合计';
  console.log(header);
  console.log('-'.repeat(header.length));
  for (const job of JOBS) {
    let sum = 0;
    let row = job.padEnd(22);
    for (const s of STAGE_NAMES) {
      const cell = result.matrix[job]?.[s];
      const c = cell?.count ?? 0;
      sum += c;
      row += String(c).padEnd(colW);
    }
    row += String(sum);
    console.log(row);
  }
  console.log('\nJSON: ' + jsonPath);
})().catch(e => { console.error('ERR:', e.message); process.exit(1); });
