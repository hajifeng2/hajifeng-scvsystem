"""从 Moka JSON 聚合面试结论标签。

Moka JSON 结构（resumes/<职位>/面试/<序号>_<姓名>.json）：
  conclusions[].result  取值 通过 / 待定 / 淘汰 / null（未提交）
  feedbacks[]           评语，普遍为空（不用）
  rounds[].interviewDate / interviewers

聚合规则（一人多面试官）：
  任一「通过」-> 通过；否则任一「淘汰」-> 淘汰；否则任一「待定」-> 待定；全 null -> 未面
"""
import json
from pathlib import Path


def aggregate_label(json_path):
    """读一份 Moka JSON，返回标签信息 dict。"""
    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)
    conclusions = d.get("conclusions", []) or []
    results = [c.get("result") for c in conclusions if c.get("result")]
    if "通过" in results:
        label = "通过"
    elif "淘汰" in results:
        label = "淘汰"
    elif "待定" in results:
        label = "待定"
    else:
        label = "未面"
    interviewers = ", ".join(
        sorted({c.get("interviewer", "") for c in conclusions if c.get("interviewer")})
    )
    rounds = d.get("rounds", []) or []
    interview_date = rounds[0].get("interviewDate", "") if rounds else ""
    return {
        "stem": Path(json_path).stem,
        "name": d.get("name", Path(json_path).stem),
        "label": label,
        "interviewers": interviewers,
        "interview_date": interview_date,
        "finished": d.get("finished", False),
        "application_id": d.get("applicationId", ""),
    }


def list_moka_files(moka_job_dir):
    """moka_job_dir: .../resumes/<职位>/面试/。
    返回 [{stem, name, json, pdf}]，按文件名排序。"""
    d = Path(moka_job_dir)
    if not d.exists():
        return []
    items = []
    for j in sorted(d.glob("*.json")):
        with open(j, encoding="utf-8") as f:
            meta = json.load(f)
        items.append({
            "stem": j.stem,
            "name": meta.get("name", j.stem),
            "json": j,
            "pdf": j.with_suffix(".pdf"),
        })
    return items
