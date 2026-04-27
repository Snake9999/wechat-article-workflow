import argparse
import html
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from 中台工具 import 读取_yaml, 写入文本, 写入_json, 项目内路径, 计算内容哈希
from 内容数据库 import 内容数据库
from 清洗文章 import 清洗_markdown


ROOT = Path("/Users/j2/.hermes/wechat-article-workflow")


def 获取文本(url: str, timeout: int, user_agent: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def 解析RSS(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    ns = {}
    if root.tag.startswith("{") and "}" in root.tag:
        ns["feed"] = root.tag.split("}", 1)[0][1:]
        entry_path = ".//feed:entry"
        title_path = "feed:title"
        link_path = "feed:link"
        date_path = "feed:updated"
        summary_path = "feed:summary"
        content_path = "feed:content"
        id_path = "feed:id"
    else:
        entry_path = ".//item"
        title_path = "title"
        link_path = "link"
        date_path = "pubDate"
        summary_path = "description"
        content_path = "content:encoded"
        id_path = "guid"

    items = []
    for item in root.findall(entry_path, ns):
        link_node = item.find(link_path, ns)
        link = ""
        if link_node is not None:
            link = (link_node.get("href") or link_node.text or "").strip()

        content_node = item.find(content_path, ns)
        content_html = ""
        if content_node is not None and content_node.text:
            content_html = html.unescape(content_node.text.strip())

        summary_node = item.find(summary_path, ns)
        summary = ""
        if summary_node is not None and summary_node.text:
            summary = html.unescape(summary_node.text.strip())

        title = (item.findtext(title_path, default="", namespaces=ns) or "").strip()
        article_id = (item.findtext(id_path, default="", namespaces=ns) or link).strip()
        published_at = (item.findtext(date_path, default="", namespaces=ns) or "").strip()

        plain_text = ET.fromstring(f"<root>{content_html}</root>").itertext() if content_html else []
        content_text = "\n".join(t.strip() for t in plain_text if t and t.strip()).strip()

        items.append({
            "id": article_id,
            "title": title,
            "link": link,
            "pubDate": published_at,
            "description": summary,
            "content_html": content_html,
            "content_text": content_text,
        })
    return items


def 保存原文(db: 内容数据库, source: dict, item: dict, raw_xml: str, workflow: dict) -> None:
    existed = db.根据URL查询原文(item["link"])
    if existed:
        return

    base_dir = workflow["base_dir"]
    title = item["title"] or "未命名文章"
    raw_text_path = 项目内路径(base_dir, "原文归档", title, "rss_item.xml")
    raw_html_path = 项目内路径(base_dir, "原文归档", title, "content.html")
    article_json_path = 项目内路径(base_dir, "原文归档", title, "feed_item.json")
    cleaned_md_path = 项目内路径(base_dir, "清洗结果", title, "cleaned.md")
    写入文本(str(raw_text_path), raw_xml)
    写入_json(str(article_json_path), item)

    content_html = item.get("content_html", "")
    if content_html:
        写入文本(str(raw_html_path), content_html)

    cleaned_source = item.get("content_text", "") or item.get("description", "") or item.get("title", "")
    cleaned_md = 清洗_markdown(cleaned_source, 原文链接=item.get("link", ""))
    写入文本(str(cleaned_md_path), cleaned_md)

    content_hash = 计算内容哈希(item.get("title", ""), item.get("link", ""), cleaned_md)
    db.执行(
        """
        INSERT INTO raw_articles (
          upstream_article_id, source_id, source_name, title, author, source_url,
          feed_url, cover_image, published_at, summary, raw_html_path, raw_text_path,
          cleaned_md_path, content_hash, fetch_status, quality_status, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.get("id", item.get("link", "")),
            source["source_id"],
            source["source_name"],
            item.get("title", "未命名文章"),
            "",
            item.get("link", ""),
            source.get("feed_url", ""),
            "",
            item.get("pubDate", ""),
            item.get("description", ""),
            str(raw_html_path) if content_html else "",
            str(raw_text_path),
            str(cleaned_md_path),
            content_hash,
            "fetched",
            "pending",
            "",
        ),
    )


def main():
    parser = argparse.ArgumentParser(description="从 WeWe RSS 拉取文章到业务库")
    parser.add_argument("--workflow", default=str(ROOT / "配置" / "workflow.yaml"))
    parser.add_argument("--sources", default=str(ROOT / "配置" / "sources.yaml"))
    args = parser.parse_args()

    workflow = 读取_yaml(args.workflow)["workflow"]
    sources = 读取_yaml(args.sources).get("sources", [])
    sqlite_path = workflow["storage"]["sqlite_path"]
    timeout = int(workflow["upstream"].get("request_timeout_seconds", 30))
    user_agent = workflow["upstream"].get("user_agent", "Hermes WeChat Workflow")

    db = 内容数据库(sqlite_path)
    pulled = 0
    for source in sources:
        if not source.get("enabled", True):
            continue
        feed_url = source.get("feed_url", "")
        if not feed_url:
            continue
        xml_text = 获取文本(feed_url, timeout=timeout, user_agent=user_agent)
        items = 解析RSS(xml_text)
        for item in items:
            保存原文(db, source, item, xml_text, workflow)
            pulled += 1

    print(json.dumps({"success": True, "pulled": pulled, "db": sqlite_path}, ensure_ascii=False))


if __name__ == "__main__":
    main()
