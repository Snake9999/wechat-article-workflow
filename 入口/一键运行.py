#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / '脚本'

COMMANDS = {
    '拉取文章': ['python3', str(SCRIPT_DIR / 'pull_from_wewe.py')],
    '补抓清洗': ['python3', str(SCRIPT_DIR / 'enrich_from_wechat_urls.py'), '--only-missing'],
    '批量改写': ['python3', str(SCRIPT_DIR / 'rewrite_articles.py')],
    '推送草稿': ['python3', str(SCRIPT_DIR / 'push_draft.py')],
}


def run(name: str) -> int:
    cmd = COMMANDS[name]
    print(f'\n==== 开始：{name} ====')
    result = subprocess.run(cmd, cwd=ROOT)
    print(f'==== 结束：{name} exit={result.returncode} ====\n')
    return result.returncode


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else '一键运行'
    if stage == '一键运行':
        steps = ['拉取文章', '补抓清洗', '批量改写', '推送草稿']
    else:
        if stage not in COMMANDS:
            raise SystemExit(f'不支持的阶段: {stage}')
        steps = [stage]

    for step in steps:
        code = run(step)
        if code != 0:
            raise SystemExit(code)


if __name__ == '__main__':
    main()
