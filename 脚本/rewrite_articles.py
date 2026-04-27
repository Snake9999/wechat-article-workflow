import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from 中台工具 import 读取_yaml, 读取文本, 写入文本, 计算内容哈希, 项目内路径
from 内容数据库 import 内容数据库
from 改写文章 import 生成_dan_koe版, 生成去AI味版


ROOT = Path("/Users/j2/.hermes/wechat-article-workflow")


def getenv_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


def main():
    parser = argparse.ArgumentParser(description="将业务库中的 raw_articles 改写成双版本")
    parser.add_argument("--workflow", default=str(ROOT / "配置" / "workflow.yaml"))
    parser.add_argument("--prompt-config", default=str(ROOT / "配置" / "改写提示词.yaml"))
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    workflow = 读取_yaml(args.workflow)["workflow"]
    prompts = 读取_yaml(args.prompt_config)
    sqlite_path = workflow["storage"]["sqlite_path"]
    db = 内容数据库(sqlite_path)

    rewrite_conf = workflow["rewrite"]
    base_url = getenv_required(rewrite_conf["base_url_env"])
    api_key = getenv_required(rewrite_conf["api_key_env"])
    model = getenv_required(rewrite_conf["model_env"])
    timeout_seconds = int(rewrite_conf.get("timeout_seconds", 180))

    rows = db.查询多条(
        """
        SELECT * FROM raw_articles
        WHERE fetch_status = 'fetched'
          AND quality_status = 'passed'
          AND COALESCE(error_message, '') = ''
        ORDER BY id DESC
        LIMIT ?
        """,
        (args.limit,),
    )

    rewritten = 0
    for row in rows:
        existing = db.查询一条("SELECT * FROM rewritten_articles WHERE raw_article_id = ?", (row["id"],))
        if existing:
            continue

        source_text = ""
        if row.get("cleaned_md_path"):
            md_path = row["cleaned_md_path"]
            if md_path and Path(md_path).exists():
                source_text = 读取文本(md_path)
        if not source_text and row.get("raw_text_path") and Path(row["raw_text_path"]).exists():
            source_text = 读取文本(row["raw_text_path"])
        if not source_text:
            raise RuntimeError(f"原文缺失或清洗结果为空，禁止改写: raw_article_id={row['id']}")

        dan_md = 生成_dan_koe版(
            system_prompt=prompts["rewrite"]["system"],
            dan_prompt=prompts["rewrite"]["dan_koe"],
            cleaned_md=source_text,
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )
        human_md = 生成去AI味版(
            system_prompt=prompts["rewrite"]["system"],
            humanize_prompt=prompts["rewrite"]["humanize"],
            dan_md=dan_md,
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )

        dan_path = 项目内路径(workflow["base_dir"], "改写结果", row["title"], "DanKoe版.md")
        human_path = 项目内路径(workflow["base_dir"], "改写结果", row["title"], "去AI味版.md")
        写入文本(str(dan_path), dan_md)
        写入文本(str(human_path), human_md)

        digest = (human_md or dan_md or source_text).strip().replace("\n", " ")[:120]
        db.执行(
            """
            INSERT INTO rewritten_articles (
              raw_article_id, rewrite_status, dan_koe_title, dan_koe_md_path,
              humanized_title, humanized_md_path, digest, tags, model_name, prompt_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                "rewritten",
                row["title"],
                str(dan_path),
                row["title"],
                str(human_path),
                digest,
                "[]",
                model,
                计算内容哈希(prompts["rewrite"]["system"], prompts["rewrite"]["dan_koe"], prompts["rewrite"]["humanize"]),
            ),
        )
        rewritten += 1

    print(f"rewritten={rewritten}")


if __name__ == "__main__":
    main()
