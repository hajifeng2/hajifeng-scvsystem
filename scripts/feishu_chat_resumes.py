"""拉取飞书招聘群里某时间之后的简历文件 + 对勾(CheckMark)标签。

机械活：分页拉 +chat-messages-list，筛 file 类型 .pdf，解析 file_key/name，
CheckMark 反应 = 通过，无 = 未通过。Agent 据此做评估分析。

用法:
  python scripts/feishu_chat_resumes.py --chat-name "客户端实习生招聘群" --start "2026-07-08T00:00:00+08:00"
  python scripts/feishu_chat_resumes.py --chat-id "oc_xxx" --start "2026-07-08T00:00:00+08:00" --output manifest.json
"""
import argparse
import json
import platform
import re
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


def run(args):
    p = subprocess.run([lark()] + args, capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        sys.exit(f"lark-cli 失败（{p.returncode}）: {p.stderr}\n{p.stdout}")
    out = p.stdout.strip()
    return json.loads(out) if out else {}


FILE_RE = re.compile(r'<file key="([^"]+)" name="([^"]+)"/>')


def parse_file(content):
    m = FILE_RE.search(content or "")
    return (m.group(1), m.group(2)) if m else None


def list_messages(chat_id, start, page_size=50):
    token = None
    while True:
        args = ["im", "+chat-messages-list", "--chat-id", chat_id,
                "--start", start, "--order", "asc", "--page-size", str(page_size)]
        if token:
            args += ["--page-token", token]
        res = run(args)
        data = res.get("data", {})
        for m in data.get("messages", []):
            yield m
        if not data.get("has_more"):
            break
        token = data.get("page_token")
        if not token:
            break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-id")
    ap.add_argument("--chat-name")
    ap.add_argument("--start", required=True, help="ISO 8601 起始时间，如 2026-07-08T00:00:00+08:00")
    ap.add_argument("--output", default="feishu_chat_manifest.json")
    args = ap.parse_args()

    chat_id = args.chat_id
    if not chat_id and args.chat_name:
        r = run(["im", "+chat-search", "--query", args.chat_name])
        chats = r.get("data", {}).get("chats", [])
        if not chats:
            sys.exit(f"没搜到群「{args.chat_name}」")
        chat_id = chats[0]["chat_id"]
        print(f"群: {chats[0]['name']}  ({chat_id})")
    if not chat_id:
        sys.exit("需要 --chat-id 或 --chat-name")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    items = []
    other_files = []
    for m in list_messages(chat_id, args.start):
        if m.get("msg_type") != "file":
            continue
        f = parse_file(m.get("content", ""))
        if not f:
            continue
        file_key, file_name = f
        rx_counts = (m.get("reactions", {}) or {}).get("counts", []) or []
        rx_details = (m.get("reactions", {}) or {}).get("details", []) or []
        rxs = [c.get("reaction_type") for c in rx_counts]
        # CheckMark 打上的时间（Unix 秒）-- 用于识别"今天刚通过"的翻转者
        ck_time = next((d.get("action_time") for d in rx_details
                        if d.get("emoji_type") == "CheckMark"), None)
        rec = {
            "message_id": m.get("message_id"),
            "create_time": m.get("create_time"),
            "file_name": file_name,
            "file_key": file_key,
            "reactions": rxs,
            "pass": "CheckMark" in rxs,
            "checkmark_time": ck_time,
        }
        if file_name.lower().endswith(".pdf"):
            items.append(rec)
        else:
            other_files.append(rec)

    Path(args.output).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = [i for i in items if i["pass"]]
    failed = [i for i in items if not i["pass"]]
    print(f"\n共 {len(items)} 份 PDF 简历（另有 {len(other_files)} 份非 PDF 文件）")
    print(f"  ✓ 通过(CheckMark): {len(passed)}")
    print(f"    未通过: {len(failed)}")
    print(f"\n--- 通过 ---")
    for i in passed:
        print(f"  ✓ {i['create_time']}  {i['file_name']}  [{','.join(i['reactions'])}]")
    print(f"\n--- 未通过 ---")
    for i in failed:
        print(f"    {i['create_time']}  {i['file_name']}  [{','.join(i['reactions']) or '无'}]")
    print(f"\nmanifest -> {args.output}")


if __name__ == "__main__":
    main()
