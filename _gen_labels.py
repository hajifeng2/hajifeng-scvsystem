import json, glob
from pathlib import Path

def gen_labels(job_dir, out_path):
    items = []
    for j in sorted(Path(job_dir).glob('*.json')):
        if j.name == 'download-record.json':
            continue
        with open(j, encoding='utf-8') as f:
            d = json.load(f)
        conclusions = d.get('conclusions', []) or []
        results = [c.get('result') for c in conclusions if c.get('result')]
        if '通过' in results:
            label = '通过'
        elif '淘汰' in results:
            label = '淘汰'
        elif '待定' in results:
            label = '待定'
        else:
            label = '未面'
        rounds = d.get('rounds', []) or []
        interview_date = rounds[0].get('interviewDate', '') if rounds else ''
        interviewers = ', '.join(
            sorted({c.get('interviewer', '') for c in conclusions if c.get('interviewer')})
        ) if conclusions else ''
        items.append({
            'stem': j.stem,
            'name': d.get('name', j.stem),
            'label': label,
            'interviewers': interviewers,
            'interview_date': interview_date,
        })

    lines = [
        f"# 简历库标签",
        f"",
        f"> Moka 抓取数据，更新时间：2026-07-14",
        f"> 标签含义：通过 / 待定 / 淘汰 / 未面（面试结论未提交）。",
        f"",
        f"| 序号 | 姓名 | 面试结论 | 面试官 | 面试时间 | 文件 |",
        f"|---|---|---|---|---|---|",
    ]
    for it in items:
        lines.append(f"| {it['stem']} | {it['name']} | {it['label']} | {it['interviewers']} | {it['interview_date']} | {it['stem']}.pdf |")

    Path(out_path).write_text('\n'.join(lines), encoding='utf-8')
    print(f"Written {len(items)} entries to {out_path}")

# 生成各职位标签
gen_labels('moka_output/服务器开发（Java）/面试', '工作区/服务器开发（Java）/简历库/简历库标签.md')
gen_labels('moka_output/客户端开发（U3D）/面试', '工作区/客户端开发（U3D）/简历库/简历库标签.md')
