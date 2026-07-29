"""Step 2：读飞书职位 + 建本地三区工作区。

用法: python step2_setup_workspace.py "职位名"

做两件事：
1. 读职位表该职位记录，打印字段值（供 Agent 据此派生 岗位画像_<职位>.md）
2. 在工作区根下建：工作区/<职位>/{简历库, 待评估, 评估完成/{被接收,未通过,待定}}/

岗位画像由 Agent（对话中）按 templates/岗位画像模板.md 派生，本脚本只建目录、不写画像。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import load_config, resolve                              # noqa: E402
from lib.lark_base import find_record_by_name                            # noqa: E402

# 派生岗位画像需要的字段（JD + 关注点 + 排除项 + 毕业时间 + 时长要求 + 其它）
JOB_FIELDS = [
    "职位名", "JD", "关注点", "排除项", "毕业时间", "时长要求",
    "职位类别", "薪资", "职级", "游戏要求", "笔试要求", "面试轮次要求", "约面注意事项",
]


def main():
    if len(sys.argv) < 2:
        print("用法: python step2_setup_workspace.py \"职位名\"")
        return
    job_name = sys.argv[1]
    cfg = load_config()
    feishu = cfg["feishu"]
    identity = feishu.get("identity", "user")

    rec = find_record_by_name(
        feishu["app_token"], feishu["职位表_table_id"],
        "职位名", job_name, identity=identity,
    )
    if not rec:
        print(f"❌ 职位表里没找到「职位名 = {job_name}」的记录。")
        print("   先在飞书职位表确认该职位存在（或用 step1_write_job.py 先写入）。")
        return

    # 打印字段供 Agent 派生画像
    print("=" * 60)
    print(f"职位记录（record_id = {rec['record_id']}）：")
    fields = rec["fields"]
    for k in JOB_FIELDS:
        v = fields.get(k, "")
        if v:
            preview = str(v)[:120] + ("..." if len(str(v)) > 120 else "")
            print(f"  {k}: {preview}")
    print("=" * 60)
    print("👉 Agent 接下来：按 templates/岗位画像模板.md，用上面字段（尤其 JD/关注点/排除项/毕业时间/时长要求）")
    print("   生成 工作区/<职位>/岗位画像_<职位>.md。")

    # 建三区目录
    ws_root = resolve(cfg["paths"]["workspace_root"])
    job_dir = ws_root / _safe_folder(job_name)
    subdirs = [
        "简历库",
        "待评估",
        "评估完成/被接收",
        "评估完成/未通过",
        "评估完成/待定",
    ]
    for sd in subdirs:
        (job_dir / sd).mkdir(parents=True, exist_ok=True)
    print(f"\n✅ 已建工作区：{job_dir}")
    for sd in subdirs:
        print(f"   - {sd}/")
    print(f"\n   record_id 记好：{rec['record_id']}（step5 写评估结果表关联用）")


def _safe_folder(name):
    """文件夹名兜底：去斜杠（路径分隔符）。"""
    return name.replace("/", "_").replace("\\", "_").strip()


if __name__ == "__main__":
    main()
