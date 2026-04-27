import json
import yaml
from pathlib import Path
from datetime import datetime
import re


def 读取_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def 写入文本(path: str, content: str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def 写入_json(path: str, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def 读取文本(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def 当前日期字符串():
    return datetime.now().strftime("%Y-%m-%d")


def 当前时间字符串():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def 创建日期目录(base_dir: str) -> Path:
    p = Path(base_dir) / 当前日期字符串()
    p.mkdir(parents=True, exist_ok=True)
    return p


def 安全文件名(name: str) -> str:
    if not name:
        return "未命名文章"
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:80] if name else "未命名文章"


def 项目内路径(base_dir: str, 一级目录: str, 标题: str, 文件名: str) -> Path:
    日期目录 = 创建日期目录(str(Path(base_dir) / 一级目录))
    文章目录 = 日期目录 / 安全文件名(标题)
    文章目录.mkdir(parents=True, exist_ok=True)
    return 文章目录 / 文件名
