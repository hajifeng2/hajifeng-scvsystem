// 给已有 PDF 补面试 JSON（PDF 在但 JSON 缺/旧）。面试阶段专用（抓 interviewCard + feedbacks）。
// 用法:
//   node moka-backfill-json.js "游戏测试实习生" "系统策划实习生"   # 默认面试阶段
//   node moka-backfill-json.js "游戏测试实习生" "初筛"             # 第二个参数若命中阶段名则当阶段
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const sleep = ms => new Promise(r => setTimeout(r, ms));

const stages = JSON.parse(fs.readFileSync(path.join(__dirname, 'stages.json'), 'utf8'));
const PIPELINE_ID = stages.pipelineId;
const stageKeys = Object.keys(stages.stages);
const args = process.argv.slice(2);
if (args.length === 0) { console.error('用法: node moka-backfill-json.js "职位1" ["职位2"] ["阶段名"]'); process.exit(1); }
// 末尾若命中阶段名，当作阶段；否则默认面试
let STAGE = '面试';
let TARGET_JOBS = args;
if (stageKeys.includes(args[args.length - 1])) { STAGE = args[args.length - 1]; TARGET_JOBS = args.slice(0, -1); }
const STAGE_ID = stages.stages[STAGE];
const BASE = path.join(__dirname, '..', 'moka_output');
const IS_INTERVIEW = STAGE === '面试';

(async () => {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const ctx = browser.contexts()[0];
  const p = await ctx.newPage();
  await p.goto('https://app.mokahr.com/candidates?pipelineId=' + PIPELINE_ID + '&stageId=' + STAGE_ID + '&jobPreference=assist&jobStatus%5B0%5D=open', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(3000);

  // fetch 全量名单
  const searchBody = { pipelineId: PIPELINE_ID, stageId: STAGE_ID, jobPreference: 'assist', jobStatus: ['open'], jobIds: [], enableAiFilter: false, onlyHmAssignment: false, limit: 200 };
  const searchResp = await p.evaluate(async (body) => {
    const r = await fetch('https://app.mokahr.com/api/outer/ats-candidate-search-left/candidate/search-candidate/v2', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    return await r.json();
  }, searchBody);
  const apps = searchResp?.data?.applications || [];
  const cands = apps.filter(c => TARGET_JOBS.includes(c.jobTitle) && c.stageId === STAGE_ID);
  console.log('目标: ' + cands.length + ' 人 (' + TARGET_JOBS.join('/') + ' / ' + STAGE + ')\n');

  for (const c of cands) {
    const job = c.jobTitle, name = c.name, appId = String(c.id);
    const outDir = path.join(BASE, job, STAGE);
    fs.mkdirSync(outDir, { recursive: true });
    const pdfs = fs.existsSync(outDir) ? fs.readdirSync(outDir).filter(f => f.endsWith('.pdf')) : [];

    // 从已有 PDF 确定序号
    let pdfMatch = pdfs.find(f => new RegExp('^\\d+_' + name + '\\.pdf$').test(f));
    let seq;
    if (pdfMatch) {
      seq = pdfMatch.match(/^(\d+)_/)[1];
    } else {
      pdfMatch = pdfs.find(f => f.includes(name));
      if (pdfMatch) {
        const seqs = pdfs.map(f => parseInt((f.match(/^(\d+)_/) || [])[1] || 0)).filter(n => n > 0);
        seq = String((seqs.length ? Math.max(...seqs) : 0) + 1).padStart(2, '0');
      } else {
        seq = String(cands.indexOf(c) + 1).padStart(2, '0');
        console.log('[' + seq + '] ' + name + ' (' + job + ')  ⚠️ 未找到PDF');
      }
    }

    // 抓取信息
    const info = { name, job, stage: STAGE, applicationId: appId, capturedAt: new Date().toISOString() };
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
      info.conclusions = ir.flatMap(r => (r.interviewerResults || []).map(x => ({ round: r.roundName, interviewer: x.interviewerName, result: x.result?.name || null })));
      info.feedbacks = IS_INTERVIEW && Array.isArray(fb?.data) ? fb.data : [];
      info.feedbackFilled = info.feedbacks.length > 0;
      if (IS_INTERVIEW) {
        const emailContent = card?.data?.[0]?.applicationEmailContent || '';
        info.interviewForm = /视频面试/.test(emailContent) ? '视频面试' : /现场|线下面试/.test(emailContent) ? '现场面试' : null;
      }
      const pdfName = seq + '_' + name + '.pdf';
      const pdfPath = path.join(outDir, pdfName);
      info.pdf = fs.existsSync(pdfPath) ? { file: pdfName, size: fs.statSync(pdfPath).size } : null;
    } catch (e) {
      info.fetchError = e.message;
    }

    fs.writeFileSync(path.join(outDir, seq + '_' + name + '.json'), JSON.stringify(info, null, 2), 'utf8');
    console.log('[' + seq + '] ' + name + '  JSON: ✅ ' + (info.feedbackFilled ? '反馈已填' : '反馈未填'));
  }

  // 重新生成 download-record.json
  for (const job of TARGET_JOBS) {
    const outDir = path.join(BASE, job, STAGE);
    if (!fs.existsSync(outDir)) continue;
    const pdfs = fs.readdirSync(outDir).filter(f => f.endsWith('.pdf')).sort();
    const record = {
      job, stage: STAGE, stageId: STAGE_ID, time: new Date().toISOString(), total: pdfs.length,
      candidates: pdfs.map(f => {
        const m = f.match(/^(\d+)_(.+)\.pdf$/);
        const seq = m ? m[1] : '?';
        const name = m ? m[2] : f.replace('.pdf', '');
        return { seq, name, pdf: f, json: seq + '_' + name + '.json' };
      }),
    };
    fs.writeFileSync(path.join(outDir, 'download-record.json'), JSON.stringify(record, null, 2), 'utf8');
    console.log('更新 record: ' + job + ' ' + pdfs.length + '份');
  }

  console.log('\n===== 补JSON完成 =====');
  await browser.close();
})().catch(e => { console.error('ERR:', e.message); process.exit(1); });
