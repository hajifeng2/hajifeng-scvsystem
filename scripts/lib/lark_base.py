"""lark-cli base 命令封装。统一走 user 身份（文档所有者，免协作者、免审）。

返回结构要点（+record-list 用 --field-id 投影时）：
  data.data            二维数组 [行][列]，按 fields 顺序
  data.record_id_list  与行并行的 record_id
  data.fields          列名
"""
import json
import platform
import shutil
import subprocess


def _resolve_lark_cli():
    """Windows 下 npm 装的是 lark-cli.cmd，Python subprocess 不认 shebang。"""
    if platform.system() == "Windows":
        cmd = shutil.which("lark-cli.cmd")
        if cmd:
            return cmd
    return "lark-cli"


_LARK_CLI = _resolve_lark_cli()


def _run(args):
    proc = subprocess.run(
        [_LARK_CLI] + args,
        capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"lark-cli 调用失败（返回码 {proc.returncode}）\n"
            f"参数: {' '.join(args)}\nstderr:\n{proc.stderr}\nstdout:\n{proc.stdout}"
        )
    out = proc.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"_raw": out}


def list_records(app_token, table_id, field_names=None, limit=200, identity="user"):
    """列记录。field_names 指定则只取这些列（返回 tabular 结构）。
    返回 [{"record_id":..., "fields":{列名:值}}, ...]。"""
    args = [
        "base", "+record-list",
        "--base-token", app_token,
        "--table-id", table_id,
        "--format", "json",
        "--limit", str(limit),
        "--as", identity,
    ]
    for f in (field_names or []):
        args += ["--field-id", f]
    res = _run(args)
    data = res.get("data", {})
    rows = data.get("data", [])
    ids = data.get("record_id_list", [])
    fields = data.get("fields", [])
    records = []
    for i, row in enumerate(rows):
        records.append({
            "record_id": ids[i] if i < len(ids) else None,
            "fields": dict(zip(fields, row)),
        })
    return records


def find_record_by_name(app_token, table_id, name_field, name, identity="user"):
    """按职位名找单条记录。返回 {"record_id":..., "fields":{...}} 或 None。"""
    for rec in list_records(app_token, table_id, field_names=[name_field], identity=identity):
        if rec["fields"].get(name_field) == name:
            return rec
    return None


def create_table(app_token, name, fields_json, identity="user", dry_run=False):
    args = [
        "base", "+table-create",
        "--base-token", app_token,
        "--name", name,
        "--fields", json.dumps(fields_json, ensure_ascii=False),
        "--as", identity,
    ]
    if dry_run:
        args.append("--dry-run")
    return _run(args)


def batch_create_records(app_token, table_id, field_names, rows, identity="user"):
    """field_names: 列名顺序；rows: [[v1,v2,...], ...]，单元格值按列顺序。
    select 用字符串；multi-select 用 [..]；link 用 [{"id":"rec_xxx"}]；datetime 用 "2026-03-24 10:00:00"。"""
    payload = {"fields": field_names, "rows": rows}
    return _run([
        "base", "+record-batch-create",
        "--base-token", app_token,
        "--table-id", table_id,
        "--json", json.dumps(payload, ensure_ascii=False),
        "--as", identity,
    ])


def list_fields(app_token, table_id, identity="user"):
    return _run([
        "base", "+field-list",
        "--base-token", app_token,
        "--table-id", table_id,
        "--as", identity,
    ])
