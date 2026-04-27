import argparse
import json
from pathlib import Path

from 中台工具 import 读取_yaml, 写入文本, 写入_json, 项目内路径, 计算内容哈希
from 内容数据库 import 内容数据库
from 抓取文章 import 抓取文章
from 清洗文章 import 清洗_markdown
from 文章质检 import 校验抓取结果


ROOT = Path("/Users/j2/.hermes/wechat-article-workflow")
最小正文长度默认值 = 500


def 回填原文(
    db: 内容数据库,
    row: dict,
    article: dict,
    workflow: dict,
    quality: dict,
) -> dict:
    base_dir = workflow["base_dir"]
    title = article.get("title") or row.get("title") or "未命名文章"
    归档键 = str(row["id"])

    raw_html_path = 项目内路径(base_dir, "原文归档", 归档键, "raw.html")
    content_html_path = 项目内路径(base_dir, "原文归档", 归档键, "content.html")
    article_json_path = 项目内路径(base_dir, "原文归档", 归档键, "article.json")
    quality_report_path = 项目内路径(base_dir, "原文归档", 归档键, "quality_report.json")
    cleaned_md_path = 项目内路径(base_dir, "清洗结果", 归档键, "cleaned.md")
    raw_text_path = 项目内路径(base_dir, "原文归档", 归档键, "content.txt")

    写入文本(str(raw_html_path), article.get("raw_html", ""))
    写入文本(str(content_html_path), article.get("content_html", ""))
    写入_json(str(article_json_path), article)

    cleaned_source = article.get("cleaned_markdown") or article.get("content_text") or ""
    cleaned_md = 清洗_markdown(cleaned_source, 原文链接=article.get("source_url", row.get("source_url", "")))
    写入文本(str(cleaned_md_path), cleaned_md)
    写入文本(str(raw_text_path), article.get("content_text", cleaned_source) or cleaned_source)

    写入_json(str(quality_report_path), quality)

    fetch_status = "fetched" if quality["extraction_ok"] else "failed"
    error_message = "" if quality["extraction_ok"] else "；".join(quality["fail_reasons"])
    content_hash = 计算内容哈希(article.get("title", ""), article.get("source_url", ""), cleaned_md)

    db.执行(
        """
        UPDATE raw_articles
        SET title = ?,
            source_name = ?,
            source_url = ?,
            cover_image = ?,
            published_at = ?,
            summary = ?,
            raw_html_path = ?,
            raw_text_path = ?,
            cleaned_md_path = ?,
            content_hash = ?,
            fetch_status = ?,
            quality_status = ?,
            error_message = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            title,
            article.get("source_name", row.get("source_name", "")),
            article.get("source_url", row.get("source_url", "")),
            article.get("cover_image", row.get("cover_image", "")),
            article.get("publish_time", row.get("published_at", "")),
            cleaned_md[:500],
            str(raw_html_path),
            str(raw_text_path),
            str(cleaned_md_path),
            content_hash,
            fetch_status,
            "passed" if quality["extraction_ok"] else "failed",
            error_message,
            row["id"],
        ),
    )

    return {
        "raw_article_id": row["id"],
        "title": title,
        "source_url": article.get("source_url", row.get("source_url", "")),
        "fetch_status": fetch_status,
        "text_length": quality["text_length"],
        "cleaned_md_path": str(cleaned_md_path),
        "quality_report_path": str(quality_report_path),
        "error_message": error_message,
    }


def main():
    parser = argparse.ArgumentParser(description="批量补抓 WeWe RSS 入库文章的公众号正文")
    parser.add_argument("--workflow", default=str(ROOT / "配置" / "workflow.yaml"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--min-text-length", type=int, default=最小正文长度默认值)
    parser.add_argument("--only-missing", action="store_true", help="只处理还没有 cleaned_md_path 的记录")
    args = parser.parse_args()

    workflow = 读取_yaml(args.workflow)["workflow"]
    sqlite_path = workflow["storage"]["sqlite_path"]
    db = 内容数据库(sqlite_path)

    sql = "SELECT * FROM raw_articles WHERE source_url LIKE 'https://mp.weixin.qq.com/%'"
    params = []
    if args.only_missing:
        sql += """
        AND (
            COALESCE(cleaned_md_path, '') = ''
            OR COALESCE(raw_html_path, '') = ''
            OR quality_status IS NULL
            OR quality_status != 'passed'
        )
        """
    sql += " ORDER BY quality_status != 'passed' DESC, id DESC LIMIT ?"
    params.append(args.limit)

    rows = db.查询多条(sql, tuple(params))

    def 持久化失败结果(row: dict, article: dict, quality: dict | None, error_message: str) -> None:
        base_dir = workflow["base_dir"]
        归档键 = str(row["id"])
        raw_html_path = 项目内路径(base_dir, "原文归档", 归档键, "raw.html")
        content_html_path = 项目内路径(base_dir, "原文归档", 归档键, "content.html")
        article_json_path = 项目内路径(base_dir, "原文归档", 归档键, "article.json")
        quality_report_path = 项目内路径(base_dir, "原文归档", 归档键, "quality_report.json")
        raw_text_path = 项目内路径(base_dir, "原文归档", 归档键, "content.txt")

        写入文本(str(raw_html_path), article.get("raw_html", ""))
        写入文本(str(content_html_path), article.get("content_html", ""))
        写入文本(str(raw_text_path), article.get("content_text", "") or article.get("cleaned_markdown", ""))
        写入_json(str(article_json_path), article)
        if quality is not None:
            写入_json(str(quality_report_path), quality)

        db.执行(
            """
            UPDATE raw_articles
            SET raw_html_path = ?,
                raw_text_path = ?,
                fetch_status = 'failed',
                quality_status = 'failed',
                error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (str(raw_html_path), str(raw_text_path), error_message, row["id"]),
        )

    results = []
    success = 0
    failed = 0
    for row in rows:
        article = {}
        quality = None
        try:
            article = 抓取文章(row["source_url"])
            quality = 校验抓取结果(article, 最小正文字数=args.min_text_length)
            if not quality["extraction_ok"]:
                raise RuntimeError("；".join(quality["fail_reasons"]))
            result = 回填原文(db, row, article, workflow, quality)
            results.append(result)
            success += 1
        except Exception as e:
            failed += 1
            持久化失败结果(row, article, quality, str(e))
            results.append({
                "raw_article_id": row["id"],
                "title": row.get("title", ""),
                "source_url": row.get("source_url", ""),
                "fetch_status": "failed",
                "error_message": str(e),
            })

    print(json.dumps({
        "success": failed == 0,
        "processed": len(rows),
        "enriched": success,
        "failed": failed,
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
