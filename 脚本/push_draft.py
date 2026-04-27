import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from 中台工具 import 读取_yaml, 写入_json
from 内容数据库 import 内容数据库
from 发布草稿 import 发布到草稿箱


ROOT = Path("/Users/j2/.hermes/wechat-article-workflow")


def getenv_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


def main():
    parser = argparse.ArgumentParser(description="将改写结果推送到公众号草稿箱")
    parser.add_argument("--workflow", default=str(ROOT / "配置" / "workflow.yaml"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--version", choices=["dan_koe", "humanized"], default="humanized")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    workflow = 读取_yaml(args.workflow)["workflow"]
    sqlite_path = workflow["storage"]["sqlite_path"]
    db = 内容数据库(sqlite_path)

    getenv_required("WECHAT_APPID")
    getenv_required("WECHAT_SECRET")

    md2wechat_conf = workflow["md2wechat"]
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

    pushed = 0
    for row in rows:
        markdown_path = row["humanized_md_path"] if args.version == "humanized" else row["dan_koe_md_path"]
        publish_row = db.查询一条(
            "SELECT * FROM publish_jobs WHERE rewritten_article_id = ? AND publish_version = ?",
            (row["id"], args.version),
        )
        if publish_row:
            continue

        raw_row = db.查询一条("SELECT * FROM raw_articles WHERE id = ?", (row["raw_article_id"],))
        cover = ""
        if raw_row and raw_row.get("cover_image"):
            cover_result = 发布到草稿箱.__globals__.get("subprocess")
            cmd = ["bash", md2wechat_conf["run_script"], "download_and_upload", raw_row["cover_image"]]
            upload = cover_result.run(cmd, capture_output=True, text=True, env=os.environ.copy())
            combined = "\n".join(part for part in [upload.stdout, upload.stderr] if part).strip()
            if upload.returncode != 0:
                raise RuntimeError(combined or "封面上传失败")
            for line in reversed((upload.stdout or "").splitlines()):
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if parsed.get("success") and parsed.get("data", {}).get("wechat_url"):
                    cover = parsed["data"]["wechat_url"]
                    break
            if not cover:
                try:
                    parsed = json.loads(upload.stdout or "{}")
                    if parsed.get("success") and parsed.get("data", {}).get("wechat_url"):
                        cover = parsed["data"]["wechat_url"]
                except json.JSONDecodeError:
                    pass

        result = 发布到草稿箱(
            md2wechat_script=md2wechat_conf["run_script"],
            markdown_path=markdown_path,
            mode=md2wechat_conf.get("mode", "api"),
            theme=md2wechat_conf.get("theme", "default"),
            cover=cover,
        )

        result_path = ROOT / "发布结果" / f"publish_job_{row['id']}_{args.version}.json"
        写入_json(str(result_path), result)

        draft_title = row["humanized_title"] if args.version == "humanized" else row["dan_koe_title"]
        db.执行(
            """
            INSERT INTO publish_jobs (
              rewritten_article_id, publish_channel, publish_version, draft_title,
              markdown_path, cover_path, draft_media_id, draft_url,
              publish_status, result_json_path, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                "wechat_draft",
                args.version,
                draft_title,
                markdown_path,
                "",
                "",
                "",
                "draft_created",
                str(result_path),
                "",
            ),
        )
        pushed += 1

    print(f"pushed={pushed}")


if __name__ == "__main__":
    main()
