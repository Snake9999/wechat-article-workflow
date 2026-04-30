import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from 中台工具 import 读取_yaml, 写入_json, 项目内路径
from 内容数据库 import 内容数据库
from 发布草稿 import 发布到草稿箱


ROOT = Path(__file__).resolve().parent.parent


def 下载封面到本地(url: str) -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        local_path = tmp.name
    subprocess.run(["curl", "-L", "--fail", url, "-o", local_path], check=True, capture_output=True, text=True)
    return local_path


def 清理临时文件(path: str) -> None:
    if path and Path(path).exists():
        Path(path).unlink()


def 解析草稿结果(result: dict) -> tuple[str, str]:
    draft_media_id = ""
    draft_url = ""
    for stream_name in ["stderr", "stdout", "raw_output"]:
        content = result.get(stream_name, "") or ""
        for line in content.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("msg") != "draft created":
                continue
            draft_media_id = payload.get("media_id") or draft_media_id
            draft_url = payload.get("draft_url") or draft_url
    return draft_media_id, draft_url


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
        generated_cover_path = 项目内路径(workflow["base_dir"], "发布结果", row["raw_title"], f"封面图_{args.version}.png")
        cover = ""
        temp_cover = ""
        try:
            if Path(generated_cover_path).exists():
                cover = str(generated_cover_path)
            elif raw_row and raw_row.get("cover_image"):
                temp_cover = 下载封面到本地(raw_row["cover_image"])
                cover = temp_cover

            result = 发布到草稿箱(
                md2wechat_script=md2wechat_conf["run_script"],
                markdown_path=markdown_path,
                mode=md2wechat_conf.get("mode", "api"),
                theme=md2wechat_conf.get("theme", "default"),
                cover=cover,
            )

            result_path = ROOT / "发布结果" / f"publish_job_{row['id']}_{args.version}.json"
            写入_json(str(result_path), result)
            draft_media_id, draft_url = 解析草稿结果(result)
            if not draft_media_id:
                raise RuntimeError("草稿创建结果缺少 media_id，不能标记为成功")

            draft_title = row["humanized_title"] if args.version == "humanized" else row["dan_koe_title"]
            stable_cover_path = ""
            if temp_cover:
                cover_dir = ROOT / "发布结果" / "封面缓存"
                cover_dir.mkdir(parents=True, exist_ok=True)
                stable_cover_path = str(cover_dir / f"publish_job_{row['id']}_{args.version}{Path(temp_cover).suffix or '.jpg'}")
                shutil.copy(temp_cover, stable_cover_path)

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
                    stable_cover_path,
                    draft_media_id,
                    draft_url,
                    "draft_created",
                    str(result_path),
                    "",
                ),
            )
            pushed += 1
        except Exception as e:
            result_path = ROOT / "发布结果" / f"publish_job_{row['id']}_{args.version}_error.json"
            写入_json(str(result_path), {"error": str(e)})
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
                    "failed",
                    str(result_path),
                    str(e),
                ),
            )
        finally:
            清理临时文件(temp_cover)

    print(f"pushed={pushed}")


if __name__ == "__main__":
    main()
