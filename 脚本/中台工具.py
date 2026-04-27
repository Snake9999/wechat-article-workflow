import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml


BASE_DIR = Path("/Users/j2/.hermes/wechat-article-workflow")


def 读取_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def 写入文本(path: str, content: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def 写入_json(path: str, data: Any) -> None:
    写入文本(path, json.dumps(data, ensure_ascii=False, indent=2))


def 读取文本(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def 当前日期目录() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def 清洗文件名(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]", "_", name.strip())
    return name[:80] or "未命名文章"


def 项目内路径(base_dir: str, *parts: str) -> Path:
    safe_parts = [当前日期目录()]
    safe_parts.extend(清洗文件名(p) for p in parts)
    return Path(base_dir).joinpath(*safe_parts)


def 计算内容哈希(*values: Iterable[str]) -> str:
    merged = "\n".join(v or "" for v in values)
    return hashlib.sha256(merged.encode("utf-8")).hexdigest()


def 初始化SQLite(sqlite_path: str, schema_path: str) -> None:
    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(sqlite_path)
    try:
        schema = 读取文本(schema_path)
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
