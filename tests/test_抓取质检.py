import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT / "脚本") not in sys.path:
    sys.path.insert(0, str(ROOT / "脚本"))

from 抓取文章 import 构建文章结果
from 文章质检 import 校验抓取结果


def test_bad_wechat_shell_page_should_fail_quality_gate():
    html = """
    <html>
      <head><title>参数错误</title></head>
      <body>
        <div>参数错误</div>
        <div>视频</div>
        <div>留言</div>
        <div>收藏</div>
      </body>
    </html>
    """
    article = 构建文章结果("https://example.com/bad", html)
    report = 校验抓取结果(article, 最小正文字数=100)

    assert report["extraction_ok"] is False
    assert "未命中正文DOM节点" in report["fail_reasons"]
    assert "正文为空" in report["fail_reasons"]


def test_valid_wechat_dom_should_pass_quality_gate():
    html = """
    <html>
      <head>
        <meta property="og:title" content="这是一篇测试文章">
      </head>
      <body>
        <h1 id="activity-name">这是一篇测试文章</h1>
        <span id="publish_time">2026-04-25</span>
        <div id="js_name">测试公众号</div>
        <div id="js_content">
          <p>第一段正文，包含足够的信息量。</p>
          <p>第二段正文，继续补充背景、方法、结论和案例说明。</p>
          <p>第三段正文，用来确保正文长度超过阈值，避免被误判为空壳页面。</p>
          <p>第四段正文，继续补充关键细节，使这篇文章可以进入后续改写流程。</p>
        </div>
      </body>
    </html>
    """
    article = 构建文章结果("https://example.com/good", html)
    report = 校验抓取结果(article, 最小正文字数=50)

    assert article["hit_selector"] == "#js_content"
    assert article["content_text"]
    assert report["extraction_ok"] is True
    assert report["text_length"] >= 50


def test_script_payload_fallback_should_be_extracted():
    script_body = "这是一段通过脚本字段兜底拿到的正文内容。" * 20
    html = f'''<html><head><title>脚本页</title></head><body><script>var msg_cdn_url = "{script_body}";</script></body></html>'''
    article = 构建文章结果("https://example.com/script", html)

    assert article["hit_selector"] == "script_msg_cdn_url"
    assert "通过脚本字段兜底" in article["content_text"]
    assert len(article["content_text"]) > 100
