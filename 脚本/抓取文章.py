import re
import json
import requests
import trafilatura
from bs4 import BeautifulSoup


异常关键词 = [
    "参数错误",
    "轻点两下取消赞",
    "轻点两下取消在看",
    "视频",
    "小程序",
    "留言",
    "收藏",
    "在看",
]

正文选择器 = [
    "#js_content",
    ".rich_media_content",
    ".rich_media_area_primary_inner",
    ".rich_media_area_primary",
    "article",
]

标题选择器 = [
    "#activity-name",
    ".rich_media_title",
    "h1",
]

来源选择器 = [
    "#js_name",
    ".wx_tap_link.js_wx_tap_highlight.weapp_text_link",
    ".profile_nickname",
]

发布时间选择器 = [
    "#publish_time",
    ".publish_time",
    ".rich_media_meta.rich_media_meta_text",
]


PC_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
    "Mobile/15E148 Safari/604.1 MicroMessenger/8.0.40"
)


def _清理文本(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _正文看起来异常(text: str) -> bool:
    if not text:
        return True
    if any(keyword in text for keyword in 异常关键词) and len(text) < 800:
        return True
    return False


def _提取标题(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"property": "og:title"})
    if meta and meta.get("content"):
        return meta.get("content", "").strip()

    for selector in 标题选择器:
        node = soup.select_one(selector)
        if node:
            title = node.get_text(" ", strip=True)
            if title:
                return title

    if soup.title:
        return soup.title.get_text(strip=True)
    return "未命名文章"


def _提取来源名称(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "author"})
    if meta and meta.get("content"):
        return meta.get("content", "").strip()

    for selector in 来源选择器:
        node = soup.select_one(selector)
        if node:
            name = node.get_text(" ", strip=True)
            if name:
                return name

    text = soup.get_text("\n", strip=True)
    m = re.search(r"微信号[:：]\s*([^\n]+)", text)
    if m:
        return m.group(1).strip()
    return ""


def _提取发布时间(html: str, soup: BeautifulSoup) -> str:
    candidates = [
        soup.find("meta", attrs={"property": "article:published_time"}),
        soup.find("meta", attrs={"property": "og:article:published_time"}),
        soup.find("meta", attrs={"name": "publishdate"}),
    ]
    for node in candidates:
        if node and node.get("content"):
            return node.get("content").strip()

    for selector in 发布时间选择器:
        node = soup.select_one(selector)
        if node:
            text = node.get_text(" ", strip=True)
            if text:
                return text

    patterns = [
        r'publish_time["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        r'ct\s*=\s*["\']?(\d{10})["\']?',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1)

    return ""


def _提取封面图(soup: BeautifulSoup) -> str:
    candidates = [
        soup.find("meta", attrs={"property": "og:image"}),
        soup.find("meta", attrs={"name": "twitter:image"}),
    ]
    for node in candidates:
        if node and node.get("content"):
            return node.get("content").strip()
    return ""


def _提取正文节点(soup: BeautifulSoup):
    for selector in 正文选择器:
        node = soup.select_one(selector)
        if node:
            return selector, node
    return "", None


def _正文转markdown(content_html: str) -> str:
    if not content_html:
        return ""
    markdown = trafilatura.extract(
        content_html,
        include_comments=False,
        include_tables=True,
        include_images=False,
        output_format="markdown",
        favor_recall=True,
        no_fallback=False,
    )
    return _清理文本(markdown or "")


def _提取图片(node) -> list[str]:
    if not node:
        return []
    images = []
    for img in node.select("img"):
        src = (
            img.get("data-src")
            or img.get("data-original")
            or img.get("src")
            or ""
        ).strip()
        if src:
            images.append(src)
    deduped = []
    seen = set()
    for item in images:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _从脚本提取正文(html: str) -> tuple[str, str]:
    patterns = [
        r'var\s+msg_cdn_url\s*=\s*"([^"]+)"',
        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;',
    ]
    for pattern in patterns:
        m = re.search(pattern, html, flags=re.S)
        if not m:
            continue
        value = m.group(1)
        if pattern.startswith('var'):
            return "script_msg_cdn_url", value
        try:
            data = json.loads(value)
            candidate = json.dumps(data, ensure_ascii=False)
            if len(candidate) > 100:
                return "script_initial_state", candidate
        except Exception:
            continue
    return "", ""


def 构建文章结果(url: str, html: str, extraction_method: str = "requests_html") -> dict:
    soup = BeautifulSoup(html, "lxml")
    title = _提取标题(soup)
    source_name = _提取来源名称(soup)
    publish_time = _提取发布时间(html, soup)
    cover_image = _提取封面图(soup)
    hit_selector, content_node = _提取正文节点(soup)
    content_html = str(content_node) if content_node else ""
    content_text = _清理文本(content_node.get_text("\n", strip=True) if content_node else "")
    cleaned_markdown = _正文转markdown(content_html)
    raw_text = _清理文本(soup.get_text("\n", strip=True))

    if (not content_text or _正文看起来异常(content_text)) and html:
        script_selector, script_content = _从脚本提取正文(html)
        if script_content and len(script_content) > len(content_text):
            hit_selector = script_selector or hit_selector
            content_text = _清理文本(script_content)
            cleaned_markdown = content_text
            content_html = content_html or ""

    return {
        "title": title,
        "source_name": source_name,
        "source_url": url,
        "publish_time": publish_time,
        "cover_image": cover_image,
        "raw_html": html,
        "content_html": content_html,
        "content_text": content_text,
        "raw_text": raw_text,
        "image_urls": _提取图片(content_node),
        "cleaned_markdown": cleaned_markdown,
        "hit_selector": hit_selector,
        "extraction_method": extraction_method,
    }


def _滚动并等待(page):
    for _ in range(5):
        page.mouse.wheel(0, 1600)
        page.wait_for_timeout(1200)


def _取页面结果(page, url: str, extraction_method: str) -> dict:
    html = page.content()
    return 构建文章结果(url=url, html=html, extraction_method=extraction_method)


def _单次浏览器抓取(url: str, user_agent: str, is_mobile: bool) -> dict | None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=user_agent,
            viewport={"width": 430 if is_mobile else 1440, "height": 2200},
            locale="zh-CN",
            is_mobile=is_mobile,
            has_touch=is_mobile,
            device_scale_factor=3 if is_mobile else 1,
            extra_http_headers={
                "Referer": "https://mp.weixin.qq.com/",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)
        _滚动并等待(page)

        for selector in 正文选择器:
            try:
                page.wait_for_selector(selector, timeout=3500)
                break
            except Exception:
                continue

        result = _取页面结果(page, url, "browser_dom_mobile" if is_mobile else "browser_dom")
        browser.close()
        return result


def _浏览器抓取(url: str) -> dict | None:
    try:
        attempts = [
            (MOBILE_UA, True),
            (PC_UA, False),
        ]
        best = None
        for ua, is_mobile in attempts:
            result = _单次浏览器抓取(url, ua, is_mobile)
            if not result:
                continue
            if result.get("content_text") and not _正文看起来异常(result.get("content_text", "")):
                return result
            if best is None or len(result.get("content_text", "")) > len(best.get("content_text", "")):
                best = result
        return best
    except Exception:
        return None


def _请求抓取(url: str) -> dict:
    headers = {
        "User-Agent": MOBILE_UA,
        "Referer": "https://mp.weixin.qq.com/",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return 构建文章结果(url=url, html=response.text, extraction_method="requests_html")


def 抓取文章(url: str) -> dict:
    browser_result = _浏览器抓取(url)
    if browser_result and browser_result.get("content_text") and not _正文看起来异常(browser_result.get("content_text", "")):
        return browser_result
    return _请求抓取(url)
