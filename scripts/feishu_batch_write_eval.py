"""批量写评估结果到飞书评估结果表（来源=待评估）。

用法: python scripts/feishu_batch_write_eval.py <records.json>
records.json: [{姓名, 所属职位, 评级, 评估结论, 评估日期, 评估卡路径}, ...]
所属职位按名查职位表 record_id 关联 link 列。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import load_config                              # noqa: E402
from lib.lark_base import batch_create_records, find_record_by_name  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("用法: python feishu_batch_write_eval.py <records.json>")
        return
    items = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    cfg = load_config()
    feishu = cfg["feishu"]
    identity = feishu.get("identity", "user")
    table_id = feishu["评估结果表_table_id"]

    # 所属职位 record_id（同批共用）
    job_name = items[0].get("所属职位", "")
    job_rec = find_record_by_name(
        feishu["app_token"], feishu["职位表_table_id"],
        "职位名", job_name, identity=identity)
    if not job_rec:
        print(f"❌ 职位表没找到「{job_name}」")
        return
    job_link = [{"id": job_rec["record_id"]}]

    field_names = ["姓名", "所属职位", "评级", "评估结论", "评估日期", "评估卡路径"]
    rows = [[it["姓名"], job_link, it["评级"], it["评估结论"],
             it.get("评估日期", "2026-07-16"), it["评估卡路径"]] for it in items]

    res = batch_create_records(
        feishu["app_token"], table_id, field_names, rows, identity=identity)
    # 响应里记录 id 在 data.record_id_list（不是 data.records）
    data = (res.get("data", {}) or {}) if isinstance(res, dict) else {}
    n = len(data.get("record_id_list", []) or [])
    print(f"✅ 批量写入 {n}/{len(rows)} 条到评估结果表（所属职位={job_name}）")


if __name__ == "__main__":
    main()
