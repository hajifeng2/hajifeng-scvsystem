// 补跑下载失败的 PDF（扫 moka_output 下所有职位的某阶段，JSON 已存在只缺 PDF）
// 重新调 search-candidate 拿新 previewUrl（OSS 签名几小时过期，record 里不存），按 appId 匹配后用 previewUrl 直链下载
// 用法:
//   node moka-retry-failed.js            # 默认「面试」阶段
//   node moka-retry-failed.js "初筛"
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const sleep = ms => new Promise(r => setTimeout(r, ms));

const stages = JSON.parse(fs.readFileSync(path.join(__dirname, 'stages.json'), 'utf8'));
const PIPELINE_ID = stages.pipelineId;
const STAGE = process.argv[2] || '面试';
const STAGE_ID = stages.stages[STAGE];
if (!STAGE_ID) { console.error('❌ 未知阶段「' + STAGE + '」'); process.exit(1); }
const BASE = path.join(__dirname, '..', 'moka_output');

const LIST_URL = 'https://app.mokahr.com/candidates?pipelineId=' + PIPELINE_ID + '&stageId=' + STAGE_ID + '&jobPreference=assist&jobStatus%5B0%5D=open';

// 扫所有职位目录
const JOBS = fs.existsSync(BASE) ? fs.readdirSync(BASE).filter(d => fs.statSync(path.join(BASE, d)).isDirectory()) : [];

(async () => {
  // 收集失败者（pdf 为空）
  const fails = [];
  for (const job of JOBS) {
    const recPath = path.join(BASE, job, STAGE, 'download-record.json');
    if (!fs.existsSync(recPath)) continue;
    const r = JSON.parse(fs.readFileSync(recPath, 'utf8'));
    for (const c of r.candidates) if (!c.pdf) fails.push({ ...c, job });
  }
  console.log('需补跑: ' + fails.length + ' 人');
  if (fails.length === 0) { console.log('✅ 无失败项'); process.exit(0); }
  fails.forEach(f => console.log('  [' + f.seq + '] ' + f.name + ' (' + f.job + ') appId=' + f.appId));

  // 按 job 分组（每个 job 调一次 search-candidate 拿新 previewUrl）
  const byJob = {};
  for (const f of fails) (byJob[f.job] = byJob[f.job] || []).push(f);

  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const ctx = browser.contexts()[0];
  const p = await ctx.newPage();
  await p.goto(LIST_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(3000);

  const results = [];
  for (const job of Object.keys(byJob)) {
    const jobFails = byJob[job];
    console.log('\n===== ' + job + ' / ' + STAGE + '：拉取名单 =====');

    // 调 search-candidate 拿当前阶段的候选人（带新 previewUrl）
    const searchBody = { pipelineId: PIPELINE_ID, stageId: STAGE_ID, jobPreference: 'assist', jobStatus: ['open'], jobIds: [], enableAiFilter: false, onlyHmAssignment: false, limit: 200 };
    let cands = [];
    try {
      const searchResp = await p.evaluate(async (body) => {
        const r = await fetch('https://app.mokahr.com/api/outer/ats-candidate-search-left/candidate/search-candidate/v2', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
        });
        return await r.json();
      }, searchBody);
      cands = (searchResp?.data?.applications || []).filter(c => c.jobTitle === job && c.stageId === STAGE_ID);
      console.log('  名单: ' + cands.length + ' 人');
    } catch (e) {
      console.log('  ❌ search-candidate 失败: ' + e.message);
      for (const f of jobFails) results.push({ seq: f.seq, name: f.name, job, ok: false, pdf: f.pdf || null, error: 'search failed' });
      continue;
    }

    for (const f of jobFails) {
      const appId = String(f.appId);
      const name = f.name;
      const seq = String(f.seq).padStart(2, '0');
      const outDir = path.join(BASE, job, STAGE);
      const pdfName = seq + '_' + name + '.pdf';
      const pdfPath = path.join(outDir, pdfName);
      console.log('\n[' + seq + '] ' + name + ' (' + job + ')');

      const c = cands.find(x => String(x.id) === appId);
      if (!c) { console.log('  PDF: ❌ 名单中未找到此 appId'); results.push({ seq, name, job, ok: false, pdf: null, error: 'not in search' }); continue; }
      if (!c.previewUrl) { console.log('  PDF: ❌ 候选人对象无 previewUrl，keys=' + Object.keys(c).join(',')); results.push({ seq, name, job, ok: false, pdf: null, error: 'no previewUrl' }); continue; }

      let ok = false;
      for (let attempt = 1; attempt <= 2 && !ok; attempt++) {
        try {
          const r = await p.evaluate(async (url) => {
            const resp = await fetch(url);
            if (!resp.ok) return { error: 'http ' + resp.status };
            const buf = await resp.arrayBuffer();
            const bytes = new Uint8Array(buf);
            let bin = '';
            for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
            return { b64: btoa(bin), size: bytes.length };
          }, c.previewUrl);
          if (r?.b64) {
            fs.writeFileSync(pdfPath, Buffer.from(r.b64, 'base64'));
            const st = fs.statSync(pdfPath);
            const sizeNote = c.resumeSize && st.size !== c.resumeSize ? ' (resumeSize=' + c.resumeSize + ' 不符)' : '';
            console.log('  PDF: ✅ ' + st.size + 'B' + sizeNote + ' (尝试' + attempt + ')');
            f.pdf = pdfName; ok = true;
          } else { console.log('  PDF: ❌ ' + (r?.error || '空响应') + ' (尝试' + attempt + ')'); }
        } catch (e) { console.log('  PDF: ❌ ' + e.message + ' (尝试' + attempt + ')'); }
      }
      results.push({ seq, name, job, ok, pdf: f.pdf || null });
    }
  }

  // 更新各 record
  for (const job of JOBS) {
    const recPath = path.join(BASE, job, STAGE, 'download-record.json');
    if (!fs.existsSync(recPath)) continue;
    const r = JSON.parse(fs.readFileSync(recPath, 'utf8'));
    for (const c of r.candidates) {
      const f = results.find(x => x.job === job && String(x.seq) === String(c.seq));
      if (f && f.pdf) c.pdf = f.pdf;
    }
    fs.writeFileSync(recPath, JSON.stringify(r, null, 2), 'utf8');
  }

  const okCount = results.filter(r => r.ok).length;
  console.log('\n===== 补跑完成: ' + okCount + '/' + results.length + ' =====');
  results.filter(r => !r.ok).forEach(r => console.log('  仍失败: [' + r.seq + '] ' + r.name + ' (' + r.job + ') ' + (r.error || '')));
  await browser.close();
})().catch(e => { console.error('ERR:', e.message); process.exit(1); });
