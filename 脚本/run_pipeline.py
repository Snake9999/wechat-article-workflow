import argparse
import subprocess
from pathlib import Path


ROOT = Path("/Users/j2/.hermes/wechat-article-workflow")


COMMANDS = {
    "init": ["python3", "脚本/初始化中台.py"],
    "pull": ["python3", "脚本/pull_from_wewe.py"],
    "enrich": ["python3", "脚本/enrich_from_wechat_urls.py", "--only-missing"],
    "rewrite": ["python3", "脚本/rewrite_articles.py"],
    "push": ["python3", "脚本/push_draft.py"],
}


def run(name: str) -> None:
    cmd = COMMANDS[name]
    result = subprocess.run(cmd, cwd=ROOT, text=True)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description="公众号内容中台编排入口")
    parser.add_argument("stage", choices=["init", "pull", "enrich", "rewrite", "push", "all"])
    args = parser.parse_args()

    if args.stage == "all":
        for name in ["init", "pull", "enrich", "rewrite", "push"]:
            run(name)
        return

    run(args.stage)


if __name__ == "__main__":
    main()
