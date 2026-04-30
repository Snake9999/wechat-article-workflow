# Skill 化说明（仓库版）

这个项目后续适合封装成一个 Hermes skill。

建议 skill 名称：
- wechat-article-workflow

建议 skill 描述：
- 从 WeWe - RSS 拉取公众号文章，补抓正文，双版本改写，并推送到公众号草稿箱。

建议的 skill 目标：
- 让其他智能体或同事，拿到仓库后可以快速完成：
  1. 环境配置
  2. 来源配置
  3. 正文补抓
  4. 双版本改写
  5. 推送公众号草稿箱

## Skill 应该包含的内容

1. 适用场景
- 当用户要把公众号来源文章自动拉取、改写、并发布到公众号草稿箱时使用

2. 前置条件
- 已安装 Python
- 已安装依赖
- 已配置 md2wechat
- 已配置公众号 AppID / Secret
- 微信后台已加 IP 白名单

3. 必填环境变量
- WECHAT_APPID
- WECHAT_SECRET
- REWRITE_API_BASE_URL
- REWRITE_API_KEY
- REWRITE_MODEL
- MD2WECHAT_API_KEY

4. 核心命令
```bash
python3 入口/01_拉取文章.py
python3 入口/02_补抓清洗.py
python3 入口/03_批量改写.py
python3 入口/04_推送草稿.py
python3 入口/一键运行.py
```

5. 已知坑
- 绝对禁止 fake 数据
- md2wechat API key 缺失会失败
- 微信 IP 白名单没配会失败
- 草稿封面优先本地文件，不要直接传远程 URL
- 刚跑通时不要立刻大重构

## 建议下一步
后续可以把这个仓库整理成：
- GitHub 项目仓库
- Hermes skill（引用该仓库或包含其使用文档）
    59|