from pathlib import Path
import sys
import os
import json
import argparse

from dotenv import load_dotenv

ROOT = Path("/Users/j2/.hermes/wechat-article-workflow")
if str(ROOT / "脚本") not in sys.path:
    sys.path.insert(0, str(ROOT / "脚本"))

from 中台工具 import 读取_yaml, 读取文本, 写入文本, 写入_json, 项目内路径, 计算内容哈希, 解析Chat模型配置
from 内容数据库 import 内容数据库
from 改写文章 import _创建客户端, _提取响应文本


默认版本 = "humanized"


def 清理正文(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def 截断正文(text: str, max_chars: int) -> str:
    text = 清理正文(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[正文过长，已截断]"


def 生成封面提示词(
    system_prompt: str,
    user_template: str,
    title: str,
    version: str,
    summary: str,
    content: str,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: int = 180,
) -> dict:
    client, resolved_model = _创建客户端(base_url, api_key, model)
    user_prompt = user_template.format(
        title=title.strip(),
        version=version.strip(),
        summary=(summary or "").strip(),
        content=(content or "").strip(),
    )
    resp = client.chat.completions.create(
        model=resolved_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        timeout=timeout_seconds,
        response_format={"type": "json_object"},
    )
    text = _提取响应文本(resp)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"封面提示词返回的不是合法 JSON: {e}") from e


def 读取文章正文(row: dict, version: str) -> str:
    if version == "humanized":
        path = row.get("humanized_md_path", "")
    else:
        path = row.get("dan_koe_md_path", "")
    if path and Path(path).exists():
        return 读取文本(path)
    raise RuntimeError(f"改写稿不存在: version={version}, path={path}")


def main():
    parser = argparse.ArgumentParser(description="为公众号文章生成封面图提示词")
    parser.add_argument("--workflow", default=str(ROOT / "配置" / "workflow.yaml"))
    parser.add_argument("--prompt-config", default=str(ROOT / "配置" / "封面图提示词.yaml"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--version", choices=["dan_koe", "humanized"], default=默认版本)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    workflow = 读取_yaml(args.workflow)["workflow"]
    prompt_conf = 读取_yaml(args.prompt_config)["cover_prompt"]
    sqlite_path = workflow["storage"]["sqlite_path"]
    db = 内容数据库(sqlite_path)

    rewrite_conf = workflow["rewrite"]
    chat_conf = 解析Chat模型配置(
        rewrite_conf["base_url_env"],
        rewrite_conf["api_key_env"],
        rewrite_conf["model_env"],
    )
    base_url = chat_conf["base_url"]
    api_key = chat_conf["api_key"]
    model = chat_conf["model"]
    timeout_seconds = int(rewrite_conf.get("timeout_seconds", 180))
    max_content_chars = int(prompt_conf.get("defaults", {}).get("max_content_chars", 5000))
    default_image_size = prompt_conf.get("defaults", {}).get("image_size", "1792x1024")

    rows = db.查询多条(
        """
        SELECT r.*, a.title AS raw_title, a.summary AS raw_summary
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
        cover_prompt_path = 项目内路径(workflow["base_dir"], "发布结果", article_title, f"封面提示词_{args.version}.json")
        if Path(cover_prompt_path).exists():
            skipped += 1
            results.append({
                "rewritten_article_id": row["id"],
                "title": article_title,
                "status": "skipped",
                "cover_prompt_path": str(cover_prompt_path),
            })
            continue

        content = 读取文章正文(row, args.version)
        content = 截断正文(content, max_content_chars)
        payload = 生成封面提示词(
            system_prompt=prompt_conf["system"],
            user_template=prompt_conf["user_template"],
            title=article_title,
            version=args.version,
            summary=row.get("raw_summary", ""),
            content=content,
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )
        payload.setdefault("image_size", default_image_size)
        payload["source_title"] = article_title
        payload["source_version"] = args.version
        payload["prompt_model"] = model
        payload["prompt_config_source"] = chat_conf["source"]
        payload["prompt_version"] = 计算内容哈希(
            prompt_conf["system"],
            prompt_conf["user_template"],
            json.dumps(prompt_conf.get("style_rules", []), ensure_ascii=False),
            json.dumps(prompt_conf.get("negative_rules", []), ensure_ascii=False),
        )

        写入_json(str(cover_prompt_path), payload)
        markdown_preview_path = 项目内路径(workflow["base_dir"], "发布结果", article_title, f"封面提示词_{args.version}.md")
        markdown_preview = "\n".join([
            f"# {payload.get('cover_title', article_title)}",
            "",
            f"- 原文标题：{article_title}",
            f"- 发布版本：{args.version}",
            f"- 视觉主题：{payload.get('visual_theme', '')}",
            f"- 建议尺寸：{payload.get('image_size', default_image_size)}",
            f"- 封面副标题：{payload.get('cover_subtitle', '')}",
            "",
            "## 主提示词",
            payload.get("main_prompt", ""),
            "",
            "## 负面提示词",
            "\n".join(f"- {x}" for x in payload.get("negative_prompt", [])),
            "",
            "## 构图说明",
            payload.get("layout_notes", ""),
            "",
            "## 文字叠加说明",
            payload.get("text_overlay_notes", ""),
            "",
            "## 色彩建议",
            "\n".join(f"- {x}" for x in payload.get("color_palette", [])),
            "",
            "## 叠字建议",
            payload.get("safe_text_overlay", ""),
        ]).strip() + "\n"
        写入文本(str(markdown_preview_path), markdown_preview)

        generated += 1
        results.append({
            "rewritten_article_id": row["id"],
            "title": article_title,
            "status": "generated",
            "cover_prompt_path": str(cover_prompt_path),
            "markdown_preview_path": str(markdown_preview_path),
        })

    print(json.dumps({
        "success": True,
        "generated": generated,
        "skipped": skipped,
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

