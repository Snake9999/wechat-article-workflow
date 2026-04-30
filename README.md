# 微信公众号内容工作流

这是一个把公众号文章从 WeWe - RSS 拉到本地，再完成正文补抓、双版本改写、封面提示词/封面图生成，最后推送到微信公众号草稿箱的工作流。

当前能力：
1. 从 WeWe - RSS 来源拉取文章
2. 补抓公众号正文并做质检
3. 生成双版本改写
   - DanKoe版
   - 去AI味版
4. 生成封面提示词与封面图
5. 推送到微信公众号草稿箱

## 适合谁用

适合这几类人直接接手：
- 只会基本命令行，不熟 Python 环境的人
- 只装了 Claude Code、Codex、Hermes、OpenClaw 一类 Agent/IDE 的人
- 需要把流程交给同事、团队成员或 Agent 自动配置的人

目标不是“你自己知道怎么跑”，而是“别人第一次拉下来也能照着跑通”。

## 运行前你要准备什么

最少需要准备 4 类东西：

1. Python 3
2. 一个可用的 WeWe - RSS 服务
3. 微信公众号发布凭据
4. 改写模型配置

如果你还要自动生成封面图，还需要额外准备图片模型配置。

## 快速开始

### 1）克隆仓库

```bash
git clone https://github.com/Snake9999/wechat-article-workflow.git
cd wechat-article-workflow
```

### 2）创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

依赖清单在 `requirements.txt`。

### 3）复制环境变量模板

```bash
cp .env.example .env
```

然后编辑 `.env`。

### 4）填写 `.env`

最少要填这些：

```bash
WECHAT_APPID=
WECHAT_SECRET=
REWRITE_API_BASE_URL=
REWRITE_API_KEY=***
REWRITE_MODEL=
```

如果你要自动生成封面图，还要再填：

```bash
OPENAI_IMAGE_API_KEY=***
OPENAI_IMAGE_BASE_URL=
OPENAI_IMAGE_MODEL=gpt-image-1
```

补充说明：
- `REWRITE_API_BASE_URL` / `REWRITE_API_KEY` / `REWRITE_MODEL` 如果没有在项目 `.env` 里完整配置，脚本会自动回退到 `~/.hermes/config.yaml` 的主 Chat 模型配置
- 封面图不会走这个回退逻辑；要生成封面图，就必须明确配置 `OPENAI_IMAGE_*`

### 5）配置 md2wechat

你还需要准备：

```text
~/.config/md2wechat/config.yaml
```

如果你走 md2wechat 的 API 模式，确保这里或环境变量里有可用的 key。

### 6）配置微信公众号后台

必须确认微信公众号后台已经加了调用机的 IP 白名单。

否则即使脚本本身没报错，创建草稿时也会失败。

## 配置文件说明

第一次接手时，主要看这 4 个配置文件：

- `配置/sources.yaml`
  - 配置上游来源
  - 也就是你要从哪些 WeWe - RSS feed 拉文章

- `配置/workflow.yaml`
  - 主流程配置
  - 包括 WeWe - RSS 地址、存储目录、改写配置、封面图配置、md2wechat 配置

- `配置/改写提示词.yaml`
  - 双版本改写时使用的提示词

- `配置/封面图提示词.yaml`
  - 封面提示词生成规则
  - 包含默认风格、结构化字段和标题约束

## 你至少要检查的 2 个地方

### A. WeWe - RSS 服务地址

默认配置在：

```text
配置/workflow.yaml
```

当前默认值是：

```yaml
upstream:
  base_url: http://127.0.0.1:4000
```

如果你的 WeWe - RSS 不在本机，必须改成你自己的服务地址。

### B. 来源列表

来源配置在：

```text
配置/sources.yaml
```

这里要改成你真实要订阅的公众号 feed，不要直接拿示例配置上线。

## 推荐执行顺序

### 方式一：一步一步执行

```bash
python3 入口/01_拉取文章.py
python3 入口/02_补抓清洗.py
python3 入口/03_批量改写.py
python3 入口/04_推送草稿.py
```

### 方式二：一键跑主流程

```bash
python3 入口/一键运行.py
```

## 封面图步骤说明

注意：封面图生成能力已经具备，但它不是 README 当前这条主流程命令里的默认独立展示步骤。

如果你想在“改写完成后、推草稿前”先本地生成封面提示词和封面图，请额外执行：

```bash
python3 脚本/generate_cover_prompt.py --limit 5 --version humanized
python3 脚本/generate_cover_image.py --limit 5 --version humanized
```

推荐插入位置：

1. `python3 入口/01_拉取文章.py`
2. `python3 入口/02_补抓清洗.py`
3. `python3 入口/03_批量改写.py`
4. `python3 脚本/generate_cover_prompt.py --limit 5 --version humanized`
5. `python3 脚本/generate_cover_image.py --limit 5 --version humanized`
6. `python3 入口/04_推送草稿.py`

## 默认行为和关键约定

这是当前仓库最重要的运行约定：

1. 所有内容必须基于真实数据
   - 禁止 fake
   - 禁止 simulate
   - 上游抓不到、正文异常、配置不完整时，应该明确失败，而不是编造内容

2. 拉取脚本默认只处理最近时间窗口内的文章
   - 当前增量窗口逻辑由拉取脚本控制
   - 如果业务要缩短或扩大处理范围，请调整相应参数和配置

3. 改写模型支持项目配置优先、Hermes 主配置回退
   - 项目 `.env` 配齐时，优先使用项目自己的模型配置
   - 项目 `.env` 不完整时，回退 `~/.hermes/config.yaml`

4. 推草稿时，封面优先使用本地生成图片
   - 优先找本地 `封面图_{version}.png`
   - 没有时才回退原文封面图

5. 不要把运行产物和密钥提交到仓库
   - `.env`
   - `发布结果/`
   - `原文归档/`
   - `清洗结果/`
   - `改写结果/`
   - `tmp_test_cover.png`
   - 各类数据库文件

## 目录说明

- `入口/`：推荐直接执行这些脚本
- `脚本/`：底层实现
- `配置/`：工作流配置
- `docs/`：补充说明文档
- `tests/`：测试
- `archive/`：历史归档

## 常见问题

### 1）为什么能改写，但不能推送草稿？

优先检查：
- 微信公众号 IP 白名单有没有配置
- `WECHAT_APPID` / `WECHAT_SECRET` 是否正确
- md2wechat 配置是否可用

### 2）为什么封面图没生成？

优先检查：
- 是否配置了 `OPENAI_IMAGE_API_KEY`
- 是否配置了 `OPENAI_IMAGE_BASE_URL`
- 是否配置了 `OPENAI_IMAGE_MODEL`
- 你有没有真的执行 `generate_cover_prompt.py` 和 `generate_cover_image.py`

### 3）为什么项目 `.env` 没填改写配置，脚本还能跑？

因为当前支持回退到：

```text
~/.hermes/config.yaml
```

如果那里配置了主 Chat 模型，改写和封面提示词阶段仍可能继续工作。

### 4）为什么明明跑了封面脚本，却没看到结果更新？

当前封面提示词和封面图脚本带幂等跳过逻辑。

也就是说：
- 目标 JSON 已存在，会直接跳过
- 目标 PNG 已存在，也会直接跳过

如果你改了提示词规则，想强制重跑，请先删除旧文件再执行。

## 文档

- `docs/使用指南.md`
- `docs/skill化说明.md`
- `docs/开源整理计划.md`
- `docs/公众号内容中台工作流.md`
- `docs/WeWeRSS部署方案.md`
