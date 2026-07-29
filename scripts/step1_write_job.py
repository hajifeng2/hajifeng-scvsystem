"""Step 1：写职位到飞书职位表。

用法:
  python step1_write_job.py 职位字段.json
  python step1_write_job.py --json '{"职位名":"...","JD":"...","薪资":"..."}'

职位字段 JSON：按职位表 15 个字段填，能填的填，不填的不传。
  职位名 / 职位类别 / 薪资 / 所属项目 / 游戏要求 / 毕业时间 / 职级 /
  笔试要求 / 面试轮次要求 / JD / 关注点 / 排除项 / 时长要求 / 约面注意事项

⚠️ select 字段（薪资/所属项目/职级/职位类别/毕业时间/笔试/面试轮次/游戏要求）
   必须用既有选项值。写前可跑：python -c "import sys; sys.path.insert(0,'.'); from lib.config import load_config; from lib.lark_base import list_fields; c=load_config(); import json; print(json.dumps(list_fields(c['feishu']['app_token'], c['feishu']['职位表_table_id']), ensure_ascii=False, indent=2))"
   看各 select 的合法选项。

写成功后打印 record_id（回填到职位同步映射 / 供 step2/step5 用）。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import load_config                      # noqa: E402
from lib.lark_base import batch_create_records          # noqa: E402


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "--json":
        fields_obj = json.loads(args[1])
    else:
        with open(args[0], encoding="utf-8") as f:
            fields_obj = json.load(f)

    cfg = load_config()
    feishu = cfg["feishu"]
    field_names = list(fields_obj.keys())
    row = [fields_obj[k] for k in field_names]

    print(f"写入职位表：{field_names}")
    res = batch_create_records(
        feishu["app_token"], feishu["职位表_table_id"],
        field_names, [row], identity=feishu.get("identity", "user"),
    )
    records = (res.get("data", {}) or {}).get("records", []) if isinstance(res, dict) else []
    rid = records[0].get("record_id") if records else None
    print("\n✅ 写入成功。")
    print(f"   record_id = {rid}")
    print(f"   职位名 = {fields_obj.get('职位名')}")
    print("   回填提示：把 record_id ↔ 职位名 记到职位同步映射；后续 step2/step5 会用到。")


if __name__ == "__main__":
    main()
