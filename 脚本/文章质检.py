import re


异常关键词 = [
    "参数错误",
    "轻点两下取消赞",
    "轻点两下取消在看",
    "视频",
    "小程序",
    "留言",
    "收藏",
    "在看",
    "内容已被发布者删除",
    "该内容因违规无法查看",
]


def _统计命中关键词(text: str) -> list[str]:
    if not text:
        return []
    hits = []
    for keyword in 异常关键词:
        if keyword in text:
            hits.append(keyword)
    return hits


def 校验抓取结果(article: dict, 最小正文字数: int = 500) -> dict:
    content_text = (article.get("content_text") or "").strip()
    cleaned_markdown = (article.get("cleaned_markdown") or "").strip()
    raw_text = (article.get("raw_text") or "").strip()
    hit_selector = (article.get("hit_selector") or "").strip()
    title = (article.get("title") or "").strip()

    主体文本 = content_text or cleaned_markdown
    suspicious_terms = _统计命中关键词(raw_text)
    reasons = []

    if not title:
        reasons.append("缺少标题")

    if not hit_selector:
        reasons.append("未命中正文DOM节点")

    if not 主体文本:
        reasons.append("正文为空")

    if len(主体文本) < 最小正文字数:
        reasons.append(f"正文字数不足{最小正文字数}字")

    if suspicious_terms and len(主体文本) < max(最小正文字数, 800):
        reasons.append("命中异常页关键词且正文过短")

    extraction_ok = len(reasons) == 0

    return {
        "extraction_ok": extraction_ok,
        "title_length": len(title),
        "text_length": len(主体文本),
        "content_text_length": len(content_text),
        "cleaned_markdown_length": len(cleaned_markdown),
        "hit_selector": hit_selector,
        "suspicious_terms": suspicious_terms,
        "fail_reasons": reasons,
        "extraction_method": article.get("extraction_method", ""),
        "source_url": article.get("source_url", ""),
    }
