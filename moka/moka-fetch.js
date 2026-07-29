// Moka 批量抓取：某职位某阶段全员的简历 PDF + JSON（面试阶段含面试结论标签）
// 用法:
//   node moka-fetch.js "客户端开发（U3D）"             # 默认「面试」阶段
//   node moka-fetch.js "客户端开发（U3D）" "初筛"
// 阶段名见 stages.json。产出到 ../moka_output/<职位>/<阶段>/。
// 通过 Edge CDP 连本机已登录的 Edge（端口 9222），用 playwright-core（不下载浏览器）。
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const sleep = ms => new Promise(r => setTimeout(r, ms));

const stages = JSON.parse(fs.readFileSync(path.join(__dirname, 'stages.json'), 'utf8'));
const PIPELINE_ID = stages.pipelineId;
const JOB = process.argv[2];
const STAGE_NAME = process.argv[3] || '面试';
const STAGE_ID = stages.stages[STAGE_NAME];
if (!JOB) { console.error('用法: node moka-fetch.js "职位名" ["阶段名"]'); process.exit(1); }
if (!STAGE_ID) { console.error('❌ 未知阶段「' + STAGE_NAME + '」。stages.json 里有: ' + Object.keys(stages.stages).join(' / ')); process.exit(1); }

const BASE = path.join(__dirname, '..', 'moka_output');
const LIST_URL = `https://app.mokahr.com/candidates?pipelineId=${PIPELINE_ID}&stageId=${STAGE_ID}&jobPreference=assist&jobStatus%5B0%5D=open`;
const IS_INTERVIEW = STAGE_NAME === '面试';

const outDir = path.join(BASE, JOB, STAGE_NAME);
fs.mkdirSync(outDir, { recursive: true });

// 已存在的 PDF（断点续传：跳过下载，但 JSON 仍生成）
const existPdf = new Set(fs.readdirSync(outDir).filter(f => f.endsWith('.pdf')));

(async () => {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const ctx = browser.contexts()[0];
  const p = await ctx.newPage();

  console.log(`\n===== ${JOB} / ${STAGE_NAME} (stageId=${STAGE_ID}) =====`);
  console.log('打开列表（建立登录上下文）...');
  await p.goto(LIST_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(3000);

  // 直接 fetch search-candidate，limit=200 拿全量（UI 拦截只能拿第一页 30 条）
  const searchBody = { pipelineId: PIPELINE_ID, stageId: STAGE_ID, jobPreference: 'assist', jobStatus: ['open'], jobIds: [], enableAiFilter: false, onlyHmAssignment: false, limit: 200 };
  const searchResp = await p.evaluate(async (body) => {
    const r = await fetch('https://app.mokahr.com/api/outer/ats-candidate-search-left/candidate/search-candidate/v2', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    return await r.json();
  }, searchBody);

  const apps = searchResp?.data?.applications || [];
  const total = searchResp?.data?.total ?? apps.length;
  const cands = apps.filter(c => c.jobTitle === JOB && c.stageId === STAGE_ID);
  console.log(`名单: ${cands.length} 人 (API返回 ${apps.length} 条, total=${total})`);
  if (cands.length === 0) { console.log('❌ 无匹配候选人（确认职位名与 Moka 一致，含括号）'); await browser.close(); process.exit(1); }

  const record = { job: JOB, stage: STAGE_NAME, stageId: STAGE_ID, time: new Date().toISOString(), total: cands.length, candidates: [] };

  for (let i = 0; i < cands.length; i++) {
    const c = cands[i];
    const seq = String(i + 1).padStart(2, '0');
    const appId = String(c.id);
    const name = c.name;
    console.log(`\n[${seq}] ${name} (appId=${appId})`);

    // 1. 抓取信息（面试阶段抓 interviewCard + feedbacks；其它阶段仅用 search 返回的 interviewRecords）
    let info = { name, job: JOB, stage: STAGE_NAME, applicationId: appId, capturedAt: new Date().toISOString() };
    try {
      let card = null, fb = null;
      if (IS_INTERVIEW) {
        [card, fb] = await p.evaluate(async (aid) => {
          const base = 'https://app.mokahr.com/api/outer/ats-interview/interview';
          const [r1, r2] = await Promise.all([
            fetch(base + '/interviewCard', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ applicationIds: [aid] }) }).then(r => r.json()).catch(e => ({ err: e.message })),
            fetch(base + '/interview-feedbacks/getExtendedFeedbacks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: aid }) }).then(r => r.json()).catch(e => ({ err: e.message })),
          ]);
          return [r1, r2];
        }, appId);
      }

      // 面试轮次与结论（来自 search-candidate 的 interviewRecords，任何阶段都可能带）
      const ir = c.interviewRecords || [];
      const nif = c.newInterviewFilterInfo || {};
      const ist = c.interviewStatus || {};
      info.rounds = ir.map(r => ({
        roundName: r.roundName,
        interviewDate: r.interviewDate ? new Date(r.interviewDate).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : null,
        interviewers: (r.interviewerResults || []).map(x => ({ name: x.interviewerName, result: x.result?.name || null, icon: x.result?.iconName || null })),
        conclusion: r.conclusion && Object.keys(r.conclusion).length ? r.conclusion : null,
      }));
      info.interviewTime = nif.interviewTime || null;
      info.interviewCount = nif.interviewCount ?? ist.count ?? null;
      info.finished = ist.finished ?? null;
      info.interviewers = (ist.interviewerInfos || nif.interviewers || []).map(x => ({ name: x.name, role: x.roleName || x.role, email: x.email || null }));
      // 面试结论（汇总）—— 标签来源
      info.conclusions = ir.flatMap(r => (r.interviewerResults || []).map(x => ({ round: r.roundName, interviewer: x.interviewerName, result: x.result?.name || null })));
      info.feedbacks = IS_INTERVIEW && Array.isArray(fb?.data) ? fb.data : [];
      info.feedbackFilled = info.feedbacks.length > 0;
      if (IS_INTERVIEW) {
        const emailContent = card?.data?.[0]?.applicationEmailContent || '';
        info.interviewForm = /视频面试/.test(emailContent) ? '视频面试' : /现场|线下面试/.test(emailContent) ? '现场面试' : null;
      }
    } catch (e) {
      info.fetchError = e.message;
    }

    // 2. 下载 PDF
    const pdfName = `${seq}_${name}.pdf`;
    const pdfPath = path.join(outDir, pdfName);
    let dlStatus;
    if (existPdf.has(pdfName)) {
      dlStatus = { file: pdfName, skipped: true };
      console.log(`  PDF: 已存在，跳过`);
    } else {
      // 详情页：面试用 /interviews（已验证）；其它阶段用通用路径（推测，失败需调）
      const detailUrl = IS_INTERVIEW
        ? `https://app.mokahr.com/candidates/application/${appId}/interviews?pipelineId=${PIPELINE_ID}&stageId=${STAGE_ID}&jobPreference=assist&jobStatus%5B0%5D=open`
        : `https://app.mokahr.com/candidates/application/${appId}?pipelineId=${PIPELINE_ID}&stageId=${STAGE_ID}&jobPreference=assist&jobStatus%5B0%5D=open`;
      try {
        await p.goto(detailUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await sleep(4000);
        const tab = await p.$('text="基本信息"');
        if (tab) await tab.click();
        await sleep(3500);
        const dl = await new Promise((resolve) => {
          const h = (d) => resolve(d);
          p.on('download', h);
          p.evaluate(() => { const ic = document.querySelector('[class*=icondownload]'); if (ic) { const b = ic.closest('button'); if (b) b.click(); } }).catch(() => {});
          setTimeout(() => { p.removeListener('download', h); resolve(null); }, 12000);
        });
        if (dl) { await dl.saveAs(pdfPath); const st = fs.statSync(pdfPath); dlStatus = { file: pdfName, size: st.size }; console.log(`  PDF: ✅ ${st.size}B`); }
        else { dlStatus = { file: null, error: 'no download' }; console.log(`  PDF: ❌ 未捕获（可跑 moka-retry-failed.js 补）`); }
      } catch (e) { dlStatus = { file: null, error: e.message }; console.log(`  PDF: ❌ ${e.message}`); }
    }

    // 3. 存 JSON
    info.pdf = dlStatus;
    fs.writeFileSync(path.join(outDir, `${seq}_${name}.json`), JSON.stringify(info, null, 2), 'utf8');
    console.log(`  JSON: ✅ ${seq}_${name}.json (反馈${info.feedbackFilled ? '已填' : '未填'})`);
    record.candidates.push({ seq, name, appId, pdf: dlStatus.file, feedbackFilled: info.feedbackFilled });
  }

  fs.writeFileSync(path.join(outDir, 'download-record.json'), JSON.stringify(record, null, 2), 'utf8');
  console.log(`\n===== 完成 ${JOB}/${STAGE_NAME}: ${record.candidates.filter(c=>c.pdf).length}/${cands.length} PDF =====`);
  await browser.close();
})().catch(e => { console.error('ERR:', e.message); process.exit(1); });
