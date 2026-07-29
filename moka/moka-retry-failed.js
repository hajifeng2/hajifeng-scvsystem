// 补跑下载失败的 PDF（扫 moka_output 下所有职位的某阶段，JSON 已存在只缺 PDF）
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
const IS_INTERVIEW = STAGE === '面试';

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

  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const ctx = browser.contexts()[0];
  const p = await ctx.newPage();
  await p.goto('https://app.mokahr.com/candidates?pipelineId=' + PIPELINE_ID + '&stageId=' + STAGE_ID + '&jobPreference=assist&jobStatus%5B0%5D=open', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(3000);

  const results = [];
  for (const f of fails) {
    const appId = String(f.appId);
    const name = f.name;
    const seq = String(f.seq).padStart(2, '0');
    const outDir = path.join(BASE, f.job, STAGE);
    const pdfName = seq + '_' + name + '.pdf';
    const pdfPath = path.join(outDir, pdfName);
    console.log('\n[' + seq + '] ' + name + ' (' + f.job + ')');

    let ok = false;
    for (let attempt = 1; attempt <= 2 && !ok; attempt++) {
      try {
        const detailUrl = IS_INTERVIEW
          ? 'https://app.mokahr.com/candidates/application/' + appId + '/interviews?pipelineId=' + PIPELINE_ID + '&stageId=' + STAGE_ID + '&jobPreference=assist&jobStatus%5B0%5D=open'
          : 'https://app.mokahr.com/candidates/application/' + appId + '?pipelineId=' + PIPELINE_ID + '&stageId=' + STAGE_ID + '&jobPreference=assist&jobStatus%5B0%5D=open';
        await p.goto(detailUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await sleep(4500);
        const tab = await p.$('text="基本信息"');
        if (tab) await tab.click();
        await sleep(3500);
        const dl = await new Promise((resolve) => {
          const h = (d) => resolve(d);
          p.on('download', h);
          p.evaluate(() => { const ic = document.querySelector('[class*=icondownload]'); if (ic) { const b = ic.closest('button'); if (b) b.click(); } }).catch(() => {});
          setTimeout(() => { p.removeListener('download', h); resolve(null); }, 12000);
        });
        if (dl) {
          await dl.saveAs(pdfPath);
          const st = fs.statSync(pdfPath);
          console.log('  PDF: ✅ ' + st.size + 'B (尝试' + attempt + ')');
          f.pdf = pdfName; ok = true;
        } else { console.log('  PDF: ❌ 未捕获 (尝试' + attempt + ')'); }
      } catch (e) { console.log('  PDF: ❌ ' + e.message + ' (尝试' + attempt + ')'); }
    }
    results.push({ seq, name, job: f.job, ok, pdf: f.pdf || null });
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
  results.filter(r => !r.ok).forEach(r => console.log('  仍失败: [' + r.seq + '] ' + r.name + ' (' + r.job + ')'));
  await browser.close();
})().catch(e => { console.error('ERR:', e.message); process.exit(1); });
