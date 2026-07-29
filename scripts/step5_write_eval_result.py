"""Step 5：写评估结果到飞书。按「来源」分派到两张表。

用法:
  python step5_write_eval_result.py 评估结果.json
  python step5_write_eval_result.py --json '{...}'

评估结果 JSON 字段：
  姓名           text
  所属职位        飞书职位名（脚本解析为 record_id 写入 link 列）
  来源           简历库 / 待评估  -- 决定写哪张表
  评级           A / B / C+ / C
  评估结论        被接收 / 未通过 / 待定
  Moka面试结论    通过 / 待定 / 淘汰 / 未面  -- 仅来源=简历库时填
  评估日期        如 2026-07-12
  评估卡路径      本地 md 路径

分派规则：
  来源=简历库  -> moka简历库表（带 Moka面试结论 列，校准对比）
  来源=待评估  -> 评估结果表（无 Moka 标签列）

⚠️ 需先跑 setup_eval_table.py 建两张表并把 table_id 回写 config.json。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import load_config                                      # noqa: E402
from lib.lark_base import batch_create_records, find_record_by_name     # noqa: E402


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "--json":
        obj = json.loads(args[1])
    else:
        with open(args[0], encoding="utf-8") as f:
            obj = json.load(f)

    cfg = load_config()
    feishu = cfg["feishu"]
    identity = feishu.get("identity", "user")

    source = obj.get("来源", "待评估")
    if source == "简历库":
        table_id = feishu.get("moka简历库表_table_id")
        if not table_id:
            print("❌ config 里 feishu.moka简历库表_table_id 为空。先跑 setup_eval_table.py 建表并回写。")
            return
        field_names = ["姓名", "所属职位", "评级", "评估结论", "Moka面试结论", "评估日期", "评估卡路径"]
    else:  # 待评估
        table_id = feishu.get("评估结果表_table_id")
        if not table_id:
            print("❌ config 里 feishu.评估结果表_table_id 为空。先跑 setup_eval_table.py 建表并回写。")
            return
        field_names = ["姓名", "所属职位", "评级", "评估结论", "评估日期", "评估卡路径"]

    # 所属职位：职位名 -> record_id（link 列 CellValue = [{"id":"rec_xxx"}]）
    job_name = obj.get("所属职位", "")
    job_rec = find_record_by_name(
        feishu["app_token"], feishu["职位表_table_id"],
        "职位名", job_name, identity=identity,
    ) if job_name else None
    if not job_rec:
        print(f"❌ 职位表里没找到「{job_name}」，无法关联。先确认职位名拼写。")
        return
    job_link = [{"id": job_rec["record_id"]}]

    # 按各表字段顺序组装一行
    if source == "简历库":
        row = [
            obj.get("姓名", ""),
            job_link,
            obj.get("评级", ""),
            obj.get("评估结论", ""),
            obj.get("Moka面试结论", ""),
            obj.get("评估日期", ""),
            obj.get("评估卡路径", ""),
        ]
    else:
        row = [
            obj.get("姓名", ""),
            job_link,
            obj.get("评级", ""),
            obj.get("评估结论", ""),
            obj.get("评估日期", ""),
            obj.get("评估卡路径", ""),
        ]

    res = batch_create_records(
        feishu["app_token"], table_id,
        field_names, [row], identity=identity,
    )
    records = (res.get("data", {}) or {}).get("records", []) if isinstance(res, dict) else []
    rid = records[0].get("record_id") if records else None
    target = "moka简历库表" if source == "简历库" else "评估结果表"
    print(f"\n✅ 已写入飞书【{target}】（来源={source}）。")
    print(f"   姓名={obj.get('姓名')} 评级={obj.get('评级')} 结论={obj.get('评估结论')}")
    if source == "简历库":
        print(f"   Moka面试结论={obj.get('Moka面试结论')}（校准对比）")
    print(f"   record_id={rid}")


if __name__ == "__main__":
    main()
