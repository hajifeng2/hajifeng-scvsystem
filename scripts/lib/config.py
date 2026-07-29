"""配置加载。config.json 在工作流根目录（本文件上两级）。"""
import json
from pathlib import Path

# 工作流根目录（本文件上两级）
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.json"


def load_config():
    """读 config.json。不存在则提示从 example 复制。"""
    if not CONFIG_PATH.exists():
        raise SystemExit(
            f"配置文件不存在：{CONFIG_PATH}\n"
            f"请复制 config.example.json 为 config.json 并按实际填写。"
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def workflow_root():
    return ROOT


def resolve(path_str):
    """相对路径相对于工作流根目录解析；绝对路径原样返回。
    避免从 scripts/ 子目录跑脚本时相对路径错位。"""
    p = Path(path_str)
    return p if p.is_absolute() else (ROOT / p)
