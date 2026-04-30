from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "脚本"
for path in (ROOT, SCRIPT_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from 脚本.pull_from_wewe import 是否在最近小时内, 解析发布时间


def test_解析发布时间_支持_iso8601_zulu():
    dt = 解析发布时间("2026-04-30T03:00:00Z")
    assert dt == datetime(2026, 4, 30, 3, 0, 0, tzinfo=timezone.utc)


def test_解析发布时间_支持_rfc2822():
    dt = 解析发布时间("Wed, 30 Apr 2026 10:00:00 +0800")
    assert dt == datetime(2026, 4, 30, 2, 0, 0, tzinfo=timezone.utc)


def test_是否在最近小时内_36小时内返回_true():
    now = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)
    published = now - timedelta(hours=35, minutes=59)
    assert 是否在最近小时内(published, 36, now=now) is True


def test_是否在最近小时内_超过36小时返回_false():
    now = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)
    published = now - timedelta(hours=36, minutes=1)
    assert 是否在最近小时内(published, 36, now=now) is False


def test_是否在最近小时内_无法解析时间默认保留():
    assert 是否在最近小时内(None, 36) is True


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ok")
