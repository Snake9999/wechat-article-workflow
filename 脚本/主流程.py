import argparse
import os
import traceback
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

from 数据库 import 初始化数据库, Article
from 工具 import 读取_yaml, 写入文本, 写入_json, 项目内路径
from 抓取文章 import 抓取文章
from 文章质检 import 校验抓取结果
from 清洗文章 import 清洗_markdown
from 改写文章 import 生成_dan_koe版, 生成去AI味版
from 发布草稿 import 发布到草稿箱


最小正文长度默认值 = 500


def 读取环境变量(name: str, required: bool = True) -> str:
    value = os.getenv(name, "").strip()
    if required and not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


def main():
    parser = argparse.ArgumentParser(description="公众号文章抓取→改写→发布草稿 工作流")
    parser.add_argument("--url", required=True, help="公众号文章 URL")
    parser.add_argument("--skip-publish", action="store_true", help="只生成改写稿，不上传草稿")
    parser.add_argument("--min-text-length", type=int, default=最小正文长度默认值, help="正文最小字数阈值")
    args = parser.parse_args()

    当前文件 = Path(__file__).resolve()
    项目根目录 = 当前文件.parent.parent
    load_dotenv(项目根目录 / ".env")

    发布配置 = 读取_yaml(str(项目根目录 / "配置" / "发布配置.yaml"))
    提示词配置 = 读取_yaml(str(项目根目录 / "配置" / "改写提示词.yaml"))

    base_dir = 发布配置["paths"]["base_dir"]
    db_path = str(Path(base_dir) / "数据" / "articles.db")
    Session = 初始化数据库(db_path)
    db = Session()

    已存在 = db.query(Article).filter_by(source_url=args.url).first()
    if 已存在 and 已存在.status not in {"failed"}:
        print(f"这篇文章已经处理过：{args.url}")
        print(f"状态：{已存在.status}")
        return
    if 已存在 and 已存在.status == "failed":
        db.delete(已存在)
        db.commit()

    record = None

    try:
        article = 抓取文章(args.url)
        标题 = article["title"] or "未命名文章"

        raw_html_path = 项目内路径(base_dir, "原文归档", 标题, "raw.html")
        content_html_path = 项目内路径(base_dir, "原文归档", 标题, "content.html")
        article_json_path = 项目内路径(base_dir, "原文归档", 标题, "article.json")
        quality_report_path = 项目内路径(base_dir, "原文归档", 标题, "quality_report.json")
        cleaned_md_path = 项目内路径(base_dir, "清洗结果", 标题, "cleaned.md")
        dan_md_path = 项目内路径(base_dir, "改写结果", 标题, "DanKoe版.md")
        human_md_path = 项目内路径(base_dir, "改写结果", 标题, "去AI味版.md")
        draft_result_path = 项目内路径(base_dir, "发布结果", 标题, "draft_result.json")

        写入文本(str(raw_html_path), article.get("raw_html", ""))
        写入文本(str(content_html_path), article.get("content_html", ""))
        写入_json(str(article_json_path), article)

        质检报告 = 校验抓取结果(article, 最小正文字数=args.min_text_length)
        写入_json(str(quality_report_path), 质检报告)

        if not 质检报告["extraction_ok"]:
            raise RuntimeError(
                "正文抓取失败，禁止进入改写环节：" + "；".join(质检报告["fail_reasons"])
            )

        cleaned_source = article.get("cleaned_markdown") or article.get("content_text") or ""
        cleaned_md = 清洗_markdown(cleaned_source, 原文链接=args.url)
        写入文本(str(cleaned_md_path), cleaned_md)

        rewrite_api_conf = 发布配置["rewrite_api"]
        base_url = 读取环境变量(rewrite_api_conf["base_url_env"])
        api_key = 读取环境变量(rewrite_api_conf["api_key_env"])
        model = 读取环境变量(rewrite_api_conf["model_env"])
        timeout_seconds = int(rewrite_api_conf.get("timeout_seconds", 180))

        dan_md = 生成_dan_koe版(
            system_prompt=提示词配置["rewrite"]["system"],
            dan_prompt=提示词配置["rewrite"]["dan_koe"],
            cleaned_md=cleaned_md,
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds
        )
        写入文本(str(dan_md_path), dan_md)

        human_md = 生成去AI味版(
            system_prompt=提示词配置["rewrite"]["system"],
            humanize_prompt=提示词配置["rewrite"]["humanize"],
            dan_md=dan_md,
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds
        )
        写入文本(str(human_md_path), human_md)

        record = Article(
            title=标题,
            source_name=article.get("source_name", ""),
            source_url=args.url,
            publish_time=article.get("publish_time", ""),
            cover_image=article.get("cover_image", ""),
            raw_html_path=str(raw_html_path),
            cleaned_md_path=str(cleaned_md_path),
            dan_koe_md_path=str(dan_md_path),
            humanized_md_path=str(human_md_path),
            status="rewritten"
        )
        db.add(record)
        db.commit()

        if not args.skip_publish:
            md2wechat_conf = 发布配置["md2wechat"]

            发布结果 = 发布到草稿箱(
                md2wechat_script=md2wechat_conf["run_script"],
                markdown_path=str(human_md_path),
                mode=md2wechat_conf.get("mode", "api"),
                theme=md2wechat_conf.get("theme", "default"),
                cover=""
            )

            写入_json(str(draft_result_path), 发布结果)

            record.draft_result_path = str(draft_result_path)
            record.status = "draft_uploaded"
            record.updated_at = datetime.utcnow()
            db.commit()

        print("流程完成")
        print(f"标题：{标题}")
        print(f"原文归档：{raw_html_path}")
        print(f"正文HTML：{content_html_path}")
        print(f"抓取结果：{article_json_path}")
        print(f"质检结果：{quality_report_path}")
        print(f"清洗结果：{cleaned_md_path}")
        print(f"DanKoe版：{dan_md_path}")
        print(f"去AI味版：{human_md_path}")
        if not args.skip_publish:
            print(f"发布结果：{draft_result_path}")

    except Exception as e:
        错误信息 = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"

        if record is None:
            record = Article(
                title="处理失败",
                source_name="",
                source_url=args.url,
                publish_time="",
                status="failed",
                error_message=错误信息
            )
            db.add(record)
        else:
            record.status = "failed"
            record.error_message = 错误信息
            record.updated_at = datetime.utcnow()

        db.commit()

        print("流程失败")
        print(错误信息)
        raise


if __name__ == "__main__":
    main()
