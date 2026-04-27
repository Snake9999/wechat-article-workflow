import argparse
from pathlib import Path

from 中台工具 import 读取_yaml, 初始化SQLite
from 内容数据库 import 内容数据库


ROOT = Path("/Users/j2/.hermes/wechat-article-workflow")


def main():
    parser = argparse.ArgumentParser(description="初始化公众号内容中台数据库")
    parser.add_argument("--workflow", default=str(ROOT / "配置" / "workflow.yaml"))
    parser.add_argument("--sources", default=str(ROOT / "配置" / "sources.yaml"))
    parser.add_argument("--schema", default=str(ROOT / "sql" / "schema.sql"))
    args = parser.parse_args()

    workflow = 读取_yaml(args.workflow)["workflow"]
    sqlite_path = workflow["storage"]["sqlite_path"]
    初始化SQLite(sqlite_path, args.schema)

    db = 内容数据库(sqlite_path)
    sources = 读取_yaml(args.sources).get("sources", [])
    for source in sources:
        db.保存source(source)

    print("数据库初始化完成")
    print(f"sqlite: {sqlite_path}")
    print(f"sources_count: {len(sources)}")


if __name__ == "__main__":
    main()
