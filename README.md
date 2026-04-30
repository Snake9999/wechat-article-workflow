# 微信公众号内容工作流

这是一个把公众号文章拉取、补抓正文、双版本改写、推送到公众号草稿箱的工作流。

当前能力：
1. 从 WeWe - RSS 来源拉取文章
2. 补抓公众号正文并做质检
3. 生成双版本改写
   - DanKoe版
   - 去AI味版
4. 生成封面提示词与封面图
5. 推送到微信公众号草稿箱

## 快速开始

1. 创建虚拟环境并安装依赖
2. 复制 `.env.example` 为 `.env`
3. 配置 `配置/` 下 yaml 文件
4. 配置 `~/.config/md2wechat/config.yaml`
5. 优先执行 `入口/` 目录中的脚本

## 推荐执行顺序

```bash
python3 入口/01_拉取文章.py
python3 入口/02_补抓清洗.py
python3 入口/03_批量改写.py
python3 入口/04_推送草稿.py
```

或：

```bash
python3 入口/一键运行.py
```

## 目录说明

- `入口/`：你平时只需要执行这里
- `脚本/`：底层实现
- `配置/`：工作流配置
- `docs/`：说明文档
- `tests/`：测试
- `archive/`：历史归档

## 注意事项

1. 绝对不要提交真实密钥
2. 微信公众号必须配置 IP 白名单
3. md2wechat 的 API key 不能缺失
4. 草稿封面优先使用本地文件路径，不要直接传远程 URL
5. `REWRITE_API_BASE_URL` / `REWRITE_API_KEY` / `REWRITE_MODEL` 若未在项目 `.env` 中完整配置，会自动回退继承 `~/.hermes/config.yaml` 的主 Chat 模型配置
6. `发布结果/`、`tmp_test_cover.png` 等本地产物不要提交到仓库

## 文档

- `docs/使用指南.md`
- `docs/skill化说明.md`
- `docs/开源整理计划.md`
- `docs/公众号内容中台工作流.md`
- `docs/WeWeRSS部署方案.md`

