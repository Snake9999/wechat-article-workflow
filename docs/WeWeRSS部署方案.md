# WeWe RSS 部署与接入方案（当前项目专用版）

> 目标：先把 WeWe RSS 作为上游公众号 Feed 中台部署起来，再接入当前 `wechat-article-workflow` 的下游抓取→改写→md2wechat→草稿箱链路。

## 1. 当前真实状态

我已经实际检查过当前环境，结果如下：

1. 当前项目里没有现成的 WeWe RSS 部署目录
2. `http://127.0.0.1:4000` 当前无法访问，返回 connection refused
3. 说明本机目前没有正在运行的 WeWe RSS 服务
4. 当前 Docker 里只发现了一个 `rsshub` 容器，不是 WeWe RSS
5. 当前 workflow 里的 `sources.yaml` 使用的是占位示例地址，不是真实可用 feed

结论：

你现在还没有把 WeWe RSS 真正部署并跑起来。

## 2. 推荐部署方式

推荐你使用 Docker Compose 单独部署 WeWe RSS。

原因：
- 最省事
- 后续迁移服务器最方便
- 数据卷可持久化
- 与当前下游 workflow 解耦
- 官方 compose 示例就是这个方向

推荐部署目录：

`~/.hermes/wewe-rss/`

注意：
- 执行根目录必须用英文路径
- 这也符合你当前 Hermes 终端对中文路径 workdir 的限制

## 3. WeWe RSS 最小可用架构

```text
Docker Compose
├── mysql:8.3
└── cooderl/wewe-rss:latest
        ├── 管理后台
        ├── 公众号订阅
        ├── 历史同步
        ├── 定时更新
        └── feed/fulltext 输出
```

对当前项目的关系：

```text
WeWe RSS (上游)
  -> feed/fulltext
  -> wechat-article-workflow/pull_from_wewe.py
  -> rewrite_articles.py
  -> push_draft.py
  -> 公众号草稿箱
```

## 4. 官方 compose 关键信息

我已经实际拉取并验证过官方 `docker-compose.yml`，核心结构是：

- MySQL 8.3
- WeWe RSS 容器暴露 `4000` 端口
- 通过 `DATABASE_URL` 连接 MySQL
- 通过 `AUTH_CODE` 做接口访问授权
- 可选 `FEED_MODE=fulltext`
- 可选 `CRON_EXPRESSION`

这说明你的方案设计判断是对的：
WeWe RSS 适合作为上游订阅与内容输出中台。

## 5. 适合你当前项目的落地目录

建议新建：

```text
~/.hermes/wewe-rss/
├── docker-compose.yml
├── .env
├── data/
│   ├── mysql/
│   └── backups/
└── README.md
```

说明：
- `docker-compose.yml`：启动 mysql + wewe-rss
- `.env`：存放数据库密码、AUTH_CODE、SERVER_ORIGIN_URL
- `data/mysql/`：如果后续改成 bind mount 可单独保留
- `data/backups/`：数据库备份

## 6. 建议配置值

### 6.1 端口

默认端口：
- WeWe RSS: `4000`
- MySQL: 不建议暴露到宿主机，内部网络用即可

### 6.2 数据库

生产建议：MySQL
原因：
- WeWe RSS 官方 compose 就是 MySQL
- 比 SQLite 更稳
- 后续数据量上来更合适

### 6.3 AUTH_CODE

必须设置一个强随机字符串。

用途：
- 保护接口访问
- 防止随便被扫和滥用

### 6.4 FEED_MODE

建议先不开全局 `fulltext`，原因：
- 全文模式更吃资源
- 部分订阅源未必都需要
- 你当前下游也会自己保存快照

更稳妥做法：
- 先按普通 feed 跑通
- 对重点号再切 fulltext 或使用 fulltext feed 地址

## 7. 推荐 docker-compose.yml

下面这份是针对你当前环境整理过的版本：

```yaml
version: '3.9'

services:
  db:
    image: mysql:8.3.0
    container_name: wewe-rss-db
    command: --mysql-native-password=ON
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: wewe-rss
      TZ: Asia/Shanghai
    volumes:
      - wewe_rss_db_data:/var/lib/mysql
    healthcheck:
      test: ['CMD', 'mysqladmin', 'ping', '-h', 'localhost']
      timeout: 45s
      interval: 10s
      retries: 10

  app:
    image: cooderl/wewe-rss:latest
    container_name: wewe-rss-app
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    ports:
      - '4000:4000'
    environment:
      DATABASE_URL: mysql://root:${MYSQL_ROOT_PASSWORD}@db:3306/wewe-rss?schema=public&connect_timeout=30&pool_timeout=30&socket_timeout=30
      AUTH_CODE: ${WEWE_AUTH_CODE}
      SERVER_ORIGIN_URL: ${WEWE_SERVER_ORIGIN_URL}
      TZ: Asia/Shanghai
      # FEED_MODE: fulltext
      # CRON_EXPRESSION: 35 5,17 * * *
      # MAX_REQUEST_PER_MINUTE: 60

volumes:
  wewe_rss_db_data:
```

## 8. 推荐 .env 模板

```bash
MYSQL_ROOT_PASSWORD=改成强密码
WEWE_AUTH_CODE=改成长随机字符串
WEWE_SERVER_ORIGIN_URL=http://127.0.0.1:4000
```

如果未来要外网访问，再把：
- `WEWE_SERVER_ORIGIN_URL`
改成你的公网域名。

## 9. 启动步骤

在英文目录执行：

```bash
cd ~/.hermes/wewe-rss
docker compose up -d
```

然后验证：

```bash
docker compose ps
curl http://127.0.0.1:4000
```

如果服务正常，再进入后台配置公众号订阅源。

## 10. 你部署完后，需要在下游项目改哪儿

你部署完 WeWe RSS 后，要修改：

文件：
`~/.hermes/wechat-article-workflow/配置/sources.yaml`

把示例地址改成真实地址，例如：

```yaml
sources:
  - source_id: some_wechat_source
    source_name: 某个公众号
    enabled: true
    upstream_type: wewe_rss
    category: AI资讯
    priority: 100
    feed_url: http://127.0.0.1:4000/feeds/真实feed路径
    fulltext_url: http://127.0.0.1:4000/feeds/真实feed路径/fulltext
    include_keywords:
      - OpenAI
      - Anthropic
    exclude_keywords:
      - 招聘
    rewrite_enabled: true
    publish_enabled: true
    owner: 你自己
    note: 来自 WeWe RSS 的真实订阅源
```

## 11. 与当前工作流的对接顺序

推荐按这个顺序来：

### 第一步：先部署 WeWe RSS
目标：4000 端口能打开

### 第二步：在 WeWe RSS 后台里添加公众号订阅
目标：拿到真实可访问 feed

### 第三步：把真实 feed 地址填入 `sources.yaml`
目标：让 `pull_from_wewe.py` 有真实上游

### 第四步：执行下游初始化
```bash
source .venv/bin/activate
python 脚本/初始化中台.py
```

### 第五步：拉取文章
```bash
source .venv/bin/activate
python 脚本/pull_from_wewe.py
```

### 第六步：改写
```bash
source .venv/bin/activate
python 脚本/rewrite_articles.py
```

### 第七步：推草稿箱
```bash
source .venv/bin/activate
python 脚本/push_draft.py
```

## 12. 推荐你现在的实施策略

最稳妥的是两阶段：

### 阶段 A：先把 WeWe RSS 跑起来
只验证：
- 容器正常
- 后台能打开
- 能加公众号订阅
- 能拿到 feed

### 阶段 B：再接下游 workflow
只验证：
- 能 pull
- 能 rewrite
- 能 push draft

这样出错时更容易定位，不会把问题混在一起。

## 13. 当前最重要的风险点

1. 4000 端口当前没有服务
2. 还没有真实公众号 feed 地址
3. 还没有 WeWe RSS 的数据库与 AUTH_CODE
4. 下游虽然已经有骨架，但现在还接不上真实上游
5. 微信草稿箱链路后续还要受 IP 白名单影响

## 14. 你现在可以直接执行的最小任务

真正的第一步不是改下游代码，而是先创建这个目录并部署：

```bash
~/.hermes/wewe-rss/
```

然后放入：
- `docker-compose.yml`
- `.env`

再启动容器。

## 15. 我对当前状态的明确判断

一句话总结：

你现在不是“不会接 WeWe RSS”，而是“上游 WeWe RSS 还没有真正部署起来”。

所以当前最正确的动作，不是继续优化下游脚本，而是先把 WeWe RSS 服务本身落地。
