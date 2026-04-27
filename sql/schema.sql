PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL UNIQUE,
  source_name TEXT NOT NULL,
  upstream_type TEXT NOT NULL DEFAULT 'wewe_rss',
  category TEXT DEFAULT '',
  priority INTEGER NOT NULL DEFAULT 0,
  enabled INTEGER NOT NULL DEFAULT 1,
  feed_url TEXT NOT NULL,
  fulltext_url TEXT DEFAULT '',
  include_keywords TEXT DEFAULT '[]',
  exclude_keywords TEXT DEFAULT '[]',
  rewrite_enabled INTEGER NOT NULL DEFAULT 1,
  publish_enabled INTEGER NOT NULL DEFAULT 0,
  owner TEXT DEFAULT '',
  note TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  upstream_article_id TEXT DEFAULT '',
  source_id TEXT NOT NULL,
  source_name TEXT NOT NULL,
  title TEXT NOT NULL,
  author TEXT DEFAULT '',
  source_url TEXT NOT NULL UNIQUE,
  feed_url TEXT DEFAULT '',
  cover_image TEXT DEFAULT '',
  published_at TEXT DEFAULT '',
  summary TEXT DEFAULT '',
  raw_html_path TEXT DEFAULT '',
  raw_text_path TEXT DEFAULT '',
  cleaned_md_path TEXT DEFAULT '',
  content_hash TEXT NOT NULL,
  fetch_status TEXT NOT NULL DEFAULT 'fetched',
  quality_status TEXT NOT NULL DEFAULT 'pending',
  error_message TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(source_id) REFERENCES sources(source_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_articles_source_id ON raw_articles(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_articles_published_at ON raw_articles(published_at);
CREATE INDEX IF NOT EXISTS idx_raw_articles_content_hash ON raw_articles(content_hash);

CREATE TABLE IF NOT EXISTS rewritten_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  raw_article_id INTEGER NOT NULL,
  rewrite_status TEXT NOT NULL DEFAULT 'pending',
  dan_koe_title TEXT DEFAULT '',
  dan_koe_md_path TEXT DEFAULT '',
  humanized_title TEXT DEFAULT '',
  humanized_md_path TEXT DEFAULT '',
  digest TEXT DEFAULT '',
  tags TEXT DEFAULT '[]',
  model_name TEXT DEFAULT '',
  prompt_version TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(raw_article_id) REFERENCES raw_articles(id)
);

CREATE INDEX IF NOT EXISTS idx_rewritten_articles_raw_article_id ON rewritten_articles(raw_article_id);
CREATE INDEX IF NOT EXISTS idx_rewritten_articles_status ON rewritten_articles(rewrite_status);

CREATE TABLE IF NOT EXISTS publish_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rewritten_article_id INTEGER NOT NULL,
  publish_channel TEXT NOT NULL DEFAULT 'wechat_draft',
  publish_version TEXT NOT NULL DEFAULT 'humanized',
  draft_title TEXT NOT NULL,
  markdown_path TEXT NOT NULL,
  cover_path TEXT DEFAULT '',
  draft_media_id TEXT DEFAULT '',
  draft_url TEXT DEFAULT '',
  publish_status TEXT NOT NULL DEFAULT 'pending',
  result_json_path TEXT DEFAULT '',
  error_message TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(rewritten_article_id) REFERENCES rewritten_articles(id)
);

CREATE INDEX IF NOT EXISTS idx_publish_jobs_status ON publish_jobs(publish_status);
CREATE INDEX IF NOT EXISTS idx_publish_jobs_rewritten_article_id ON publish_jobs(rewritten_article_id);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  status TEXT NOT NULL,
  detail_json TEXT DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
