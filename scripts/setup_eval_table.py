"""一次性建飞书两张评估表：评估结果表（待评估）+ moka简历库表（简历库，带 Moka 标签）。
write 操作，运行前先 dry-run 预览并要求确认。

建表后打印两个 table_id，需手动回写 config.json：
  feishu.评估结果表_table_id
  feishu.moka简历库表_table_id

用法: python setup_eval_table.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import load_config                     # noqa: E402
from lib.lark_base import create_table                 # noqa: E402

# 评级 / Moka面试结论 选项
TIER_OPTS = [{"name": "A"}, {"name": "B"}, {"name": "C+"}, {"name": "C"}]
MOKA_OPTS = [{"name": "通过"}, {"name": "待定"}, {"name": "淘汰"}, {"name": "未面"}]


def fields_for_eval_table(job_table_id):
    """评估结果表（待评估）：无 Moka 标签、无来源（整表都是待评估）。"""
    return [
        {"name": "姓名", "type": "text"},                       # 主属性列
        {"name": "所属职位", "type": "link", "link_table": job_table_id},
        {"name": "评级", "type": "select", "multiple": False, "options": TIER_OPTS},
        {"name": "评估详情", "type": "text"},
        {"name": "核心原因总结", "type": "text"},
        {"name": "评估日期", "type": "text"},
        {"name": "评估卡路径", "type": "text"},
    ]


def fields_for_library_table(job_table_id):
    """moka简历库表（简历库）：比评估结果表多一列 Moka面试结论（校准对比用）。"""
    return [
        {"name": "姓名", "type": "text"},
        {"name": "所属职位", "type": "link", "link_table": job_table_id},
        {"name": "评级", "type": "select", "multiple": False, "options": TIER_OPTS},
        {"name": "Moka面试结论", "type": "select", "multiple": False, "options": MOKA_OPTS},
        {"name": "评估详情", "type": "text"},
        {"name": "核心原因总结", "type": "text"},
        {"name": "评估卡内容", "type": "text"},
        {"name": "评估日期", "type": "text"},
        {"name": "评估卡路径", "type": "text"},
    ]


def print_fields(name, fields):
    print(f"  【{name}】")
    for f in fields:
        extra = ""
        if f["type"] == "select":
            extra = " 选项: " + "/".join(o["name"] for o in f["options"])
        if f["type"] == "link":
            extra = f" 关联职位表={f['link_table']}"
        print(f"    - {f['name']} ({f['type']}){extra}")


def main():
    cfg = load_config()
    feishu = cfg["feishu"]
    app_token = feishu["app_token"]
    job_table_id = feishu["职位表_table_id"]
    identity = feishu.get("identity", "user")

    if feishu.get("评估结果表_table_id") and feishu.get("moka简历库表_table_id"):
        print("⚠️  config 里两张表的 table_id 都已有。如要重建，先清空并手动删旧表。")
        return

    eval_fields = fields_for_eval_table(job_table_id)
    lib_fields = fields_for_library_table(job_table_id)

    print("=" * 60)
    print(f"将在多维表 {app_token} 里新建两张表：")
    print_fields("评估结果表（待评估）", eval_fields)
    print_fields("moka简历库表（简历库，带 Moka 标签）", lib_fields)
    print("=" * 60)

    ans = input("确认建两张表？(y/N): ").strip().lower()
    if ans != "y":
        print("已取消。")
        return

    results = {}
    for name, fields in [("评估结果表", eval_fields), ("moka简历库表", lib_fields)]:
        res = create_table(app_token, name, fields, identity=identity)
        data = res.get("data", {}) if isinstance(res, dict) else {}
        table_id = data.get("table_id") or data.get("id")
        if not table_id:  # 兜底：列所有表找新建的
            from lib.lark_base import _run  # noqa
            tl = _run(["base", "+table-list", "--base-token", app_token, "--as", identity])
            for t in tl.get("data", {}).get("tables", []):
                if t.get("name") == name:
                    table_id = t.get("id")
                    break
        results[name] = table_id
        print(f"  ✅ {name} table_id = {table_id}")

    print("\n请回写 config.json：")
    print(f'  feishu.评估结果表_table_id = "{results["评估结果表"]}"')
    print(f'  feishu.moka简历库表_table_id = "{results["moka简历库表"]}"')


if __name__ == "__main__":
    main()
