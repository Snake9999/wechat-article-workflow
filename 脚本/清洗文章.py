import re


def 清洗_markdown(md: str, 原文链接: str = "") -> str:
    if not md:
        return ""

    text = md

    删除模式 = [
        r"点击上方.*?关注.*?\n",
        r"点击蓝字.*?关注.*?\n",
        r"扫码.*?二维码.*?\n",
        r"长按.*?二维码.*?\n",
        r"责任编辑.*?\n",
        r"责编.*?\n",
        r"排版.*?\n",
        r"校对.*?\n",
        r"编辑[:：].*?\n",
        r"来源[:：].*?\n",
        r"推荐阅读[:：]?.*",
        r"阅读原文.*",
        r"欢迎分享.*?\n",
        r"本文转载.*?\n",
        r"商务合作.*?\n",
    ]

    for pattern in 删除模式:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if 原文链接:
        头部说明 = (
            f"# 原文整理稿\n\n"
            f"原文链接：{原文链接}\n\n"
            f"以下内容为程序抓取并清洗后的文本，后续改写必须严格基于这份内容，禁止补充未经验证的信息。\n\n"
        )
        text = 头部说明 + text

    return text
