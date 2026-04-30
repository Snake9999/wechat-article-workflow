     1|# WeWe - RSS 部署与接入方案（当前项目专用版）
     2|
     3|> 目标：先把 WeWe - RSS 作为上游公众号 Feed 中台部署起来，再接入当前 `wechat-article-workflow` 的下游抓取→改写→md2wechat→草稿箱链路。
     4|
     5|## 1. 当前真实状态
     6|
     7|我已经实际检查过当前环境，结果如下：
     8|
     9|1. 当前项目里没有现成的 WeWe - RSS 部署目录
    10|2. `http://127.0.0.1:4000` 当前无法访问，返回 connection refused
    11|3. 说明本机目前没有正在运行的 WeWe - RSS 服务
    12|4. 当前 Docker 里只发现了一个 `rsshub` 容器，不是 WeWe - RSS
    13|5. 当前 workflow 里的 `sources.yaml` 使用的是占位示例地址，不是真实可用 feed
    14|
    15|结论：
    16|
    17|你现在还没有把 WeWe - RSS 真正部署并跑起来。
    18|
    19|## 2. 推荐部署方式
    20|
    21|推荐你使用 Docker Compose 单独部署 WeWe - RSS。
    22|
    23|原因：
    24|- 最省事
    25|- 后续迁移服务器最方便
    26|- 数据卷可持久化
    27|- 与当前下游 workflow 解耦
    28|- 官方 compose 示例就是这个方向
    29|
    30|推荐部署目录：
    31|
    32|`~/.hermes/wewe-rss/`
    33|
    34|注意：
    35|- 执行根目录必须用英文路径
    36|- 这也符合你当前 Hermes 终端对中文路径 workdir 的限制
    37|
    38|## 3. WeWe - RSS 最小可用架构
    39|
    40|```text
    41|Docker Compose
    42|├── mysql:8.3
    43|└── cooderl/wewe-rss:latest
    44|        ├── 管理后台
    45|        ├── 公众号订阅
    46|        ├── 历史同步
    47|        ├── 定时更新
    48|        └── feed/fulltext 输出
    49|```
    50|
    51|对当前项目的关系：
    52|
    53|```text
    54|WeWe - RSS (上游)
    55|  -> feed/fulltext
    56|  -> wechat-article-workflow/pull_from_wewe.py
    57|  -> rewrite_articles.py
    58|  -> push_draft.py
    59|  -> 公众号草稿箱
    60|```
    61|
    62|## 4. 官方 compose 关键信息
    63|
    64|我已经实际拉取并验证过官方 `docker-compose.yml`，核心结构是：
    65|
    66|- MySQL 8.3
    67|- WeWe - RSS 容器暴露 `4000` 端口
    68|- 通过 `DATABASE_URL` 连接 MySQL
    69|- 通过 `AUTH_CODE` 做接口访问授权
    70|- 可选 `FEED_MODE=fulltext`
    71|- 可选 `CRON_EXPRESSION`
    72|
    73|这说明你的方案设计判断是对的：
    74|WeWe - RSS 适合作为上游订阅与内容输出中台。
    75|
    76|## 5. 适合你当前项目的落地目录
    77|
    78|建议新建：
    79|
    80|```text
    81|~/.hermes/wewe-rss/
    82|├── docker-compose.yml
    83|├── .env
    84|├── data/
    85|│   ├── mysql/
    86|│   └── backups/
    87|└── README.md
    88|```
    89|
    90|说明：
    91|- `docker-compose.yml`：启动 mysql + wewe-rss
    92|- `.env`：存放数据库密码、AUTH_CODE、SERVER_ORIGIN_URL
    93|- `data/mysql/`：如果后续改成 bind mount 可单独保留
    94|- `data/backups/`：数据库备份
    95|
    96|## 6. 建议配置值
    97|
    98|### 6.1 端口
    99|
   100|默认端口：
   101|- WeWe - RSS: `4000`
   102|- MySQL: 不建议暴露到宿主机，内部网络用即可
   103|
   104|### 6.2 数据库
   105|
   106|生产建议：MySQL
   107|原因：
   108|- WeWe - RSS 官方 compose 就是 MySQL
   109|- 比 SQLite 更稳
   110|- 后续数据量上来更合适
   111|
   112|### 6.3 AUTH_CODE
   113|
   114|必须设置一个强随机字符串。
   115|
   116|用途：
   117|- 保护接口访问
   118|- 防止随便被扫和滥用
   119|
   120|### 6.4 FEED_MODE
   121|
   122|建议先不开全局 `fulltext`，原因：
   123|- 全文模式更吃资源
   124|- 部分订阅源未必都需要
   125|- 你当前下游也会自己保存快照
   126|
   127|更稳妥做法：
   128|- 先按普通 feed 跑通
   129|- 对重点号再切 fulltext 或使用 fulltext feed 地址
   130|
   131|## 7. 推荐 docker-compose.yml
   132|
   133|下面这份是针对你当前环境整理过的版本：
   134|
   135|```yaml
   136|version: '3.9'
   137|
   138|services:
   139|  db:
   140|    image: mysql:8.3.0
   141|    container_name: wewe-rss-db
   142|    command: --mysql-native-password=ON
   143|    restart: unless-stopped
   144|    environment:
   145|      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
   146|      MYSQL_DATABASE: wewe-rss
   147|      TZ: Asia/Shanghai
   148|    volumes:
   149|      - wewe_rss_db_data:/var/lib/mysql
   150|    healthcheck:
   151|      test: ['CMD', 'mysqladmin', 'ping', '-h', 'localhost']
   152|      timeout: 45s
   153|      interval: 10s
   154|      retries: 10
   155|
   156|  app:
   157|    image: cooderl/wewe-rss:latest
   158|    container_name: wewe-rss-app
   159|    restart: unless-stopped
   160|    depends_on:
   161|      db:
   162|        condition: service_healthy
   163|    ports:
   164|      - '4000:4000'
   165|    environment:
   166|      DATABASE_URL: mysql://root:***@db:3306/wewe-rss?schema=public&connect_timeout=30&pool_timeout=30&socket_timeout=30
   167|      AUTH_CODE: ${WEWE_AUTH_CODE}
   168|      SERVER_ORIGIN_URL: ${WEWE_SERVER_ORIGIN_URL}
   169|      TZ: Asia/Shanghai
   170|      # FEED_MODE: fulltext
   171|      # CRON_EXPRESSION: 35 5,17 * * *
   172|      # MAX_REQUEST_PER_MINUTE: 60
   173|
   174|volumes:
   175|  wewe_rss_db_data:
   176|```
   177|
   178|## 8. 推荐 .env 模板
   179|
   180|```bash
   181|MYSQL_ROOT_PASSWORD=***
   182|WEWE_AUTH_CODE=***
   183|WEWE_SERVER_ORIGIN_URL=http://127.0.0.1:4000
   184|```
   185|
   186|如果未来要外网访问，再把：
   187|- `WEWE_SERVER_ORIGIN_URL`
   188|改成你的公网域名。
   189|
   190|## 9. 启动步骤
   191|
   192|在英文目录执行：
   193|
   194|```bash
   195|cd ~/.hermes/wewe-rss
   196|docker compose up -d
   197|```
   198|
   199|然后验证：
   200|
   201|```bash
   202|docker compose ps
   203|curl http://127.0.0.1:4000
   204|```
   205|
   206|如果服务正常，再进入后台配置公众号订阅源。
   207|
   208|## 10. 你部署完后，需要在下游项目改哪儿
   209|
   210|你部署完 WeWe - RSS 后，要修改：
   211|
   212|文件：
   213|`~/.hermes/wechat-article-workflow/配置/sources.yaml`
   214|
   215|把示例地址改成真实地址，例如：
   216|
   217|```yaml
   218|sources:
   219|  - source_id: some_wechat_source
   220|    source_name: 某个公众号
   221|    enabled: true
   222|    upstream_type: wewe_rss
   223|    category: AI资讯
   224|    priority: 100
   225|    feed_url: http://127.0.0.1:4000/feeds/真实feed路径
   226|    fulltext_url: http://127.0.0.1:4000/feeds/真实feed路径/fulltext
   227|    include_keywords:
   228|      - OpenAI
   229|      - Anthropic
   230|    exclude_keywords:
   231|      - 招聘
   232|    rewrite_enabled: true
   233|    publish_enabled: true
   234|    owner: 你自己
   235|    note: 来自 WeWe - RSS 的真实订阅源
   236|```
   237|
   238|## 11. 与当前工作流的对接顺序
   239|
   240|推荐按这个顺序来：
   241|
   242|### 第一步：先部署 WeWe - RSS
   243|目标：4000 端口能打开
   244|
   245|### 第二步：在 WeWe - RSS 后台里添加公众号订阅
   246|目标：拿到真实可访问 feed
   247|
   248|### 第三步：把真实 feed 地址填入 `sources.yaml`
   249|目标：让 `pull_from_wewe.py` 有真实上游
   250|
   251|### 第四步：执行下游初始化
   252|```bash
   253|source .venv/bin/activate
   254|python 脚本/初始化中台.py
   255|```
   256|
   257|### 第五步：拉取文章
   258|```bash
   259|source .venv/bin/activate
   260|python 脚本/pull_from_wewe.py
   261|```
   262|
   263|### 第六步：改写
   264|```bash
   265|source .venv/bin/activate
   266|python 脚本/rewrite_articles.py
   267|```
   268|
   269|### 第七步：推草稿箱
   270|```bash
   271|source .venv/bin/activate
   272|python 脚本/push_draft.py
   273|```
   274|
   275|## 12. 推荐你现在的实施策略
   276|
   277|最稳妥的是两阶段：
   278|
   279|### 阶段 A：先把 WeWe - RSS 跑起来
   280|只验证：
   281|- 容器正常
   282|- 后台能打开
   283|- 能加公众号订阅
   284|- 能拿到 feed
   285|
   286|### 阶段 B：再接下游 workflow
   287|只验证：
   288|- 能 pull
   289|- 能 rewrite
   290|- 能 push draft
   291|
   292|这样出错时更容易定位，不会把问题混在一起。
   293|
   294|## 13. 当前最重要的风险点
   295|
   296|1. 4000 端口当前没有服务
   297|2. 还没有真实公众号 feed 地址
   298|3. 还没有 WeWe - RSS 的数据库与 AUTH_CODE
   299|4. 下游虽然已经有骨架，但现在还接不上真实上游
   300|5. 微信草稿箱链路后续还要受 IP 白名单影响
   301|
   302|## 14. 你现在可以直接执行的最小任务
   303|
   304|真正的第一步不是改下游代码，而是先创建这个目录并部署：
   305|
   306|```bash
   307|~/.hermes/wewe-rss/
   308|```
   309|
   310|然后放入：
   311|- `docker-compose.yml`
   312|- `.env`
   313|
   314|再启动容器。
   315|
   316|## 15. 我对当前状态的明确判断
   317|
   318|一句话总结：
   319|
   320|你现在不是“不会接 WeWe - RSS”，而是“上游 WeWe - RSS 还没有真正部署起来”。
   321|
   322|所以当前最正确的动作，不是继续优化下游脚本，而是先把 WeWe - RSS 服务本身落地。
   323|