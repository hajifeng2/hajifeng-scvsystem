"""Step 3：复制 Moka 简历库到工作区 + 生成标签清单。

用法: python step3_copy_moka_library.py "职位名"

流程：
1. 按 config.moka_job_map[职位名] 找到 Moka 目录名
2. 从 config.paths.moka_resumes_root/<Moka目录>/面试/ 复制 PDF+JSON 到 工作区/<职位>/简历库/
3. 聚合每份 JSON 的面试结论（通过/待定/淘汰/未面），生成 简历库标签.md

⚠️ 标签只在面试结论提交后有意义。面试没面完就跑，标签会大片是「未面」。
   刷新标签：重抓 Moka（moka-dl-with-interview.js）后重跑本脚本。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import load_config, resolve                              # noqa: E402
from lib.moka_label import aggregate_label, list_moka_files             # noqa: E402
from step2_setup_workspace import _safe_folder                           # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("用法: python step3_copy_moka_library.py \"职位名\" [\"阶段名\"]")
        print("  阶段名默认「面试」（校准标签所在阶段），见 moka/stages.json")
        return
    job_name = sys.argv[1]
    stage = sys.argv[2] if len(sys.argv) > 2 else "面试"
    cfg = load_config()
    moka_map = cfg.get("moka_job_map", {})
    moka_dir = moka_map.get(job_name)
    if not moka_dir:
        print(f"❌ config.moka_job_map 里没有「{job_name}」的映射。")
        print(f"   已有映射：{moka_map}")
        print("   请在 config.json 的 moka_job_map 加 \"<飞书职位名>\": \"<Moka目录名>\"。")
        return

    moka_interview_dir = resolve(cfg["paths"]["moka_resumes_root"]) / moka_dir / stage
    if not moka_interview_dir.exists():
        print(f"❌ Moka 简历目录不存在：{moka_interview_dir}")
        print(f"   先跑 Moka 抓取：node moka/moka-fetch.js \"{moka_dir}\" \"{stage}\"")
        print("   （需先启动 CDP Edge + 登录 Moka，见 moka/README.md）")
        return

    ws_root = resolve(cfg["paths"]["workspace_root"])
    lib_dir = ws_root / _safe_folder(job_name) / "简历库"
    lib_dir.mkdir(parents=True, exist_ok=True)

    files = list_moka_files(moka_interview_dir)
    if not files:
        print(f"⚠️  Moka 目录里没找到 JSON：{moka_interview_dir}")
        return

    print(f"复制 {len(files)} 份简历到 {lib_dir} ...")
    import shutil
    rows = []
    for f in files:
        # 复制 PDF + JSON（原件不动）
        for src in (f["pdf"], f["json"]):
            if src.exists():
                shutil.copy2(src, lib_dir / src.name)
        info = aggregate_label(f["json"])
        rows.append(info)
        print(f"  {info['stem']}: {info['name']} -> {info['label']}")

    # 标签分布
    from collections import Counter
    dist = Counter(r["label"] for r in rows)
    print(f"\n标签分布：{dict(dist)}")
    if dist.get("未面", 0) > 0:
        print(f"⚠️  有 {dist['未面']} 份「未面」（面试结论未提交）。建议面试轮次走完再评估，或重抓后重跑本脚本。")

    # 写简历库标签.md
    write_manifest(lib_dir / "简历库标签.md", job_name, rows)
    print(f"\n✅ 简历库就绪：{lib_dir}")
    print(f"   标签清单：{lib_dir / '简历库标签.md'}")


def write_manifest(path, job_name, rows):
    lines = [
        f"# 简历库标签 · {job_name}",
        "",
        "> Moka 抓取的该职位候选人（带面试结论标签）。Agent 评估时据此分组（通过组 vs 淘汰组）做群体分析。",
        "> 标签含义：通过 / 待定 / 淘汰 / 未面（面试结论未提交）。",
        "",
        "| 序号 | 姓名 | 面试结论 | 面试官 | 面试时间 | 文件 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['stem']} | {r['name']} | {r['label']} | {r['interviewers']} | {r['interview_date']} | {r['stem']}.pdf |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
