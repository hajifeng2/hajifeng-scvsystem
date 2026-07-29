"""按 manifest 下载飞书群里的简历文件到指定目录。

用法:
  python scripts/feishu_chat_download.py --manifest <manifest.json> --to <目录>
"""
import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def lark():
    if platform.system() == "Windows":
        c = shutil.which("lark-cli.cmd")
        if c:
            return c
    return "lark-cli"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--to", required=True)
    args = ap.parse_args()
    items = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    out = Path(args.to)
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    for i in items:
        name = i["file_name"].replace("/", "_").replace("\\", "_")
        dst = out / name
        if dst.exists() and dst.stat().st_size > 0:
            print(f"  skip(exists): {name}")
            ok += 1
            continue
        # --output 只接受相对路径，cd 到目标目录用裸文件名
        r = subprocess.run(
            [lark(), "im", "+messages-resources-download",
             "--message-id", i["message_id"], "--file-key", i["file_key"],
             "--type", "file", "--output", name],
            cwd=str(out), capture_output=True, text=True, encoding="utf-8",
        )
        if r.returncode != 0:
            print(f"  FAIL: {name}\n    {r.stderr}")
        else:
            print(f"  ok: {name}")
            ok += 1
    print(f"\n下载 {ok}/{len(items)} -> {out}")


if __name__ == "__main__":
    main()
