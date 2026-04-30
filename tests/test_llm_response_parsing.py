from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "脚本"
for path in (ROOT, SCRIPT_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from 脚本.改写文章 import _提取响应文本


class Message:
    def __init__(self, content):
        self.content = content


class Choice:
    def __init__(self, content):
        self.message = Message(content)


class ResponseObject:
    def __init__(self, content):
        self.choices = [Choice(content)]


class ResponseWithOutputText:
    def __init__(self, text):
        self.output_text = text


def test_对象响应提取_choices_content():
    assert _提取响应文本(ResponseObject("hello")) == "hello"


def test_字符串_sse_响应提取_data_json_content():
    raw = 'data: {"choices":[{"message":{"content":"hello world"}}]}\n\n'
    assert _提取响应文本(raw) == "hello world"


def test_对象响应提取_output_text():
    assert _提取响应文本(ResponseWithOutputText("ok text")) == "ok text"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ok")
