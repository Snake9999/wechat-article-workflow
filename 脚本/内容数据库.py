import sqlite3
from pathlib import Path
from typing import Any


class 内容数据库:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path

    def 连接(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def 执行(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        conn = self.连接()
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def 查询一条(self, sql: str, params: tuple[Any, ...] = ()):
        conn = self.连接()
        try:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def 查询多条(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict]:
        conn = self.连接()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def 保存source(self, source: dict) -> int:
        return self.执行(
            """
            INSERT INTO sources (
              source_id, source_name, upstream_type, category, priority, enabled,
              feed_url, fulltext_url, include_keywords, exclude_keywords,
              rewrite_enabled, publish_enabled, owner, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
              source_name=excluded.source_name,
              upstream_type=excluded.upstream_type,
              category=excluded.category,
              priority=excluded.priority,
              enabled=excluded.enabled,
              feed_url=excluded.feed_url,
              fulltext_url=excluded.fulltext_url,
              include_keywords=excluded.include_keywords,
              exclude_keywords=excluded.exclude_keywords,
              rewrite_enabled=excluded.rewrite_enabled,
              publish_enabled=excluded.publish_enabled,
              owner=excluded.owner,
              note=excluded.note,
              updated_at=CURRENT_TIMESTAMP
            """,
            (
                source["source_id"],
                source["source_name"],
                source.get("upstream_type", "wewe_rss"),
                source.get("category", ""),
                source.get("priority", 0),
                1 if source.get("enabled", True) else 0,
                source["feed_url"],
                source.get("fulltext_url", ""),
                json_text(source.get("include_keywords", [])),
                json_text(source.get("exclude_keywords", [])),
                1 if source.get("rewrite_enabled", True) else 0,
                1 if source.get("publish_enabled", False) else 0,
                source.get("owner", ""),
                source.get("note", ""),
            ),
        )

    def 根据URL查询原文(self, source_url: str):
        return self.查询一条("SELECT * FROM raw_articles WHERE source_url = ?", (source_url,))


def json_text(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)
