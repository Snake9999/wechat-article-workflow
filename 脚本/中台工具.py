import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml


BASE_DIR = Path("/Users/j2/.hermes/wechat-article-workflow")
HERMES_CONFIG_PATH = Path.home() / ".hermes" / "config.yaml"


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


def 读取Hermes主模型配置() -> dict:
    if not HERMES_CONFIG_PATH.exists():
        return {}
    try:
        config = 读取_yaml(str(HERMES_CONFIG_PATH))
    except Exception:
        return {}
    model_conf = config.get("model") or {}
    return {
        "provider": str(model_conf.get("provider", "") or "").strip(),
        "base_url": str(model_conf.get("base_url", "") or "").strip(),
        "api_key": str(model_conf.get("api_key", "") or "").strip(),
        "model": str(model_conf.get("default", "") or "").strip(),
    }


def 解析Chat模型配置(base_url_env: str, api_key_env: str, model_env: str) -> dict:
    env_base_url = os.getenv(base_url_env, "").strip()
    env_api_key = os.getenv(api_key_env, "").strip()
    env_model = os.getenv(model_env, "").strip()

    if env_base_url and env_api_key and env_model:
        return {
            "provider": "custom",
            "base_url": env_base_url,
            "api_key": env_api_key,
            "model": env_model,
            "source": "project_env",
        }

    hermes_model = 读取Hermes主模型配置()
    if hermes_model.get("base_url") and hermes_model.get("api_key") and hermes_model.get("model"):
        return {
            "provider": hermes_model.get("provider") or "custom",
            "base_url": hermes_model["base_url"],
            "api_key": hermes_model["api_key"],
            "model": hermes_model["model"],
            "source": "hermes_config",
        }

    missing = []
    if not env_base_url:
        missing.append(base_url_env)
    if not env_api_key:
        missing.append(api_key_env)
    if not env_model:
        missing.append(model_env)
    raise RuntimeError(
        "缺少 Chat 模型配置：项目 .env 未完整提供 "
        + ", ".join(missing)
        + "，且 ~/.hermes/config.yaml 的 model.base_url / model.api_key / model.default 也不可用"
    )

