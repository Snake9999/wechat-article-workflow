from pathlib import Path
import os
import base64
import json
import mimetypes
import argparse
import sys

import requests
from dotenv import load_dotenv

ROOT = Path("/Users/j2/.hermes/wechat-article-workflow")
if str(ROOT / "脚本") not in sys.path:
    sys.path.insert(0, str(ROOT / "脚本"))

from 中台工具 import 读取_yaml, 写入_json, 项目内路径
from 内容数据库 import 内容数据库


def getenv_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


def post_json(url: str, api_key: str, payload: dict, timeout: int) -> dict:
    resp = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json=payload,
        timeout=timeout,
    )
    text = resp.text
    if not resp.ok:
        raise RuntimeError(f"图片接口请求失败: status={resp.status_code}, body={text[:1000]}")
    try:
        return resp.json()
    except json.JSONDecodeError as e:
        raise RuntimeError(f"图片接口返回非 JSON: {text[:500]}") from e


def 下载图片(url: str, target_path: Path, timeout: int) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(
        url,
        headers={"User-Agent": "Hermes Cover Image Generator"},
        timeout=timeout,
    )
    if not resp.ok:
        raise RuntimeError(f"下载图片失败: status={resp.status_code}, url={url}")
    target_path.write_bytes(resp.content)


def 保存base64图片(image_base64: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(base64.b64decode(image_base64))


def 生成图片(prompt_data: dict, base_url: str, api_key: str, model: str, image_size: str, timeout: int) -> dict:
    endpoint = base_url.rstrip("/") + "/v1/images/generations"
    cover_title = (prompt_data.get("cover_title") or "").strip()
    cover_subtitle = (prompt_data.get("cover_subtitle") or "").strip()
    text_overlay_notes = (prompt_data.get("text_overlay_notes") or "").strip()
    layout_notes = (prompt_data.get("layout_notes") or "").strip()

    prompt = prompt_data["main_prompt"]
    overlay_parts = []
    if cover_title:
        overlay_parts.append(f"主标题文字必须直接生成在图片里 内容必须完全等于 {cover_title}")
    if cover_subtitle:
        overlay_parts.append(f"副标题文字也必须直接生成在图片里 内容必须完全等于 {cover_subtitle}")
    overlay_parts.append("主标题和副标题都绝对禁止出现任何标点符号")
    overlay_parts.append("禁止自动补充句号 逗号 冒号 分号 叹号 问号 破折号 书名号 引号 括号 斜杠")
    overlay_parts.append("禁止改写标题 禁止替换字符 禁止增删字符 禁止自动纠正格式")
    overlay_parts.append("如果模型倾向加标点 请仍然输出无标点版本 因为有标点就是错误结果")
    overlay_parts.append("这不是仅预留标题区 而是要把中文标题作为画面设计的一部分直接渲染出来")
    overlay_parts.append("标题文字必须清晰 完整 可读 不能乱码 不能缺字 不能用无意义假字替代")
    overlay_parts.append("标题排版要像公众号科技商业封面 信息层级清楚 适合直接发布预览")
    if layout_notes:
        overlay_parts.append(f"构图要求 {layout_notes}")
    if text_overlay_notes:
        overlay_parts.append(f"文字排版要求 {text_overlay_notes}")

    prompt = prompt.rstrip() + "\n\n" + "\n".join(overlay_parts)
    payload = {
        "model": model,
        "prompt": prompt,
        "size": image_size,
    }
    result = post_json(endpoint, api_key, payload, timeout)
    data = result.get("data") or []
    if not data:
        raise RuntimeError(f"图片接口未返回 data: {result}")
    first = data[0] or {}
    image_url = first.get("url", "")
    image_base64 = first.get("b64_json", "")
    if not image_url and not image_base64:
        raise RuntimeError(f"图片接口未返回 url 或 b64_json: {result}")
    return {
        "request": payload,
        "response": result,
        "image_url": image_url,
        "image_base64": image_base64,
    }


def main():
    parser = argparse.ArgumentParser(description="根据封面提示词生成公众号封面图")
    parser.add_argument("--workflow", default=str(ROOT / "配置" / "workflow.yaml"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--version", choices=["dan_koe", "humanized"], default="humanized")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    workflow = 读取_yaml(args.workflow)["workflow"]
    db = 内容数据库(workflow["storage"]["sqlite_path"])
    cover_conf = workflow.get("cover_image", {})

    api_key = getenv_required(cover_conf["api_key_env"])
    base_url = getenv_required(cover_conf["base_url_env"])
    model = getenv_required(cover_conf["model_env"])
    timeout = int(cover_conf.get("timeout_seconds", 180))
    image_size = cover_conf.get("image_size", "1792x1024")
    output_format = cover_conf.get("output_format", "png").lstrip(".")

    rows = db.查询多条(
        """
        SELECT r.*, a.title AS raw_title
        FROM rewritten_articles r
        JOIN raw_articles a ON a.id = r.raw_article_id
        WHERE r.rewrite_status = 'rewritten'
        ORDER BY r.id DESC
        LIMIT ?
        """,
        (args.limit,),
    )

    generated = 0
    skipped = 0
    results = []

    for row in rows:
        article_title = row.get("humanized_title") or row.get("dan_koe_title") or row.get("raw_title") or "未命名文章"
        prompt_path = 项目内路径(workflow["base_dir"], "发布结果", article_title, f"封面提示词_{args.version}.json")
        image_path = 项目内路径(workflow["base_dir"], "发布结果", article_title, f"封面图_{args.version}.{output_format}")
        meta_path = 项目内路径(workflow["base_dir"], "发布结果", article_title, f"封面图_{args.version}.json")

        if image_path.exists():
            skipped += 1
            results.append({
                "rewritten_article_id": row["id"],
                "title": article_title,
                "status": "skipped",
                "image_path": str(image_path),
            })
            continue

        if not Path(prompt_path).exists():
            results.append({
                "rewritten_article_id": row["id"],
                "title": article_title,
                "status": "missing_prompt",
                "prompt_path": str(prompt_path),
            })
            continue

        prompt_data = json.loads(Path(prompt_path).read_text(encoding="utf-8"))
        gen = 生成图片(prompt_data, base_url=base_url, api_key=api_key, model=model, image_size=image_size, timeout=timeout)

        if gen["image_base64"]:
            保存base64图片(gen["image_base64"], Path(image_path))
        else:
            下载图片(gen["image_url"], Path(image_path), timeout=timeout)

        mime_type, _ = mimetypes.guess_type(str(image_path))
        meta = {
            "title": article_title,
            "version": args.version,
            "image_path": str(image_path),
            "mime_type": mime_type or "image/png",
            "model": model,
            "base_url": base_url,
            "prompt_path": str(prompt_path),
            "safe_text_overlay": prompt_data.get("safe_text_overlay", ""),
            "generation": gen,
        }
        写入_json(str(meta_path), meta)
        generated += 1
        results.append({
            "rewritten_article_id": row["id"],
            "title": article_title,
            "status": "generated",
            "image_path": str(image_path),
            "meta_path": str(meta_path),
        })

    print(json.dumps({
        "success": True,
        "generated": generated,
        "skipped": skipped,
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
