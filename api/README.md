# HarnessMate API（Flask）

智能体平台的 HTTP 后端：账号与鉴权、智能体/会话/消息的增删改查、文件上传、聊天消息转发（到 Hub）与 SSE 下行推送、Hub 完成帧落库。

接口清单见 [`docs/HermesMate-Api文档.md`](docs/HermesMate-Api文档.md)。

---

## 一、技术栈

| 组件 | 选型 |
|---|---|
| Web 框架 | Flask 3.1 + Flask-Login（请求级登录态）+ injector（依赖注入） |
| ORM | Flask-SQLAlchemy 3.1 + Alembic 迁移 |
| 数据库 | PostgreSQL（`account` / `agent` / `server` / `conversation` / `message`） |
| 缓存与消息 | Redis（SSE pub/sub 频道） |
| WSGI | gunicorn `gthread`，默认 4 worker × 4 线程 |
| 对象存储 | 腾讯云 COS（文件上传） |

## 二、目录结构

```
api/
├── app/http/app.py          入口（Flask 实例、扩展初始化、蓝图注册）
├── config/                  配置（default_config.py 默认值，config.py 读环境变量）
├── internal/
│   ├── handler/             控制器：参数校验 + 调 service + 统一响应
│   ├── service/             业务逻辑（account / agent / conversation / message / chat / jwt / oauth …）
│   ├── model/               SQLAlchemy 模型
│   ├── schema/              FlaskForm 请求校验
│   ├── router/router.py     全部路由集中注册（蓝图 llmops）
│   ├── middleware/          request_loader：从请求解析 token 并装载 Account
│   ├── extension/           Flask 扩展（redis / logging / migrate）
│   ├── lib/                 id 生成、时间工具
│   └── migration/           Alembic 迁移脚本
├── pkg/                     统一响应与状态码、sqlalchemy、password、oauth
├── docs/                    API 文档
└── storage/                 本地文件暂存（容器内卷）
```

## 三、请求生命周期

```
请求
 └─ 蓝图 llmops
     └─ Middleware.request_loader
         ├─ 取 Authorization: Bearer <token>；没有则取 ?token=（给 EventSource 兜底）
         ├─ JwtService.parse_token → 校验签名与 exp
         └─ 装载 Account
     └─ Handler（FlaskForm 校验）
         └─ Service（业务 + 事务）
             └─ Model / Redis / 外部服务（Hub、COS）
     └─ pkg.response.success_json / validate_error_json
```

## 四、响应约定（重要）

面向浏览器的接口统一返回 HTTP 200，业务结果放在 body：

```json
{"code": "success", "data": {}, "message": ""}
```

`code` 取值：`success` / `fail` / `not_found` / `unauthorized` / `forbidden` / `validate_error`。

这套约定由全局 `register_error_handler(Exception, ...)` 兜底实现——**任何异常（含 404、500）都会被包成 HTTP 200**。前端 `request.ts` 按 `body.code` 判断，因此工作正常；但**机器调用方不能只看状态码**。

> 唯一例外：`POST /internal/messages` 是服务间接口，在方法内部自行 try/except，返回真实状态码（403/400/500）。原因见 `docs/HermesMate-Api文档.md` 6.3 与 `hub/README.md` 的「内部接口契约」。

## 五、鉴权与登录态

- 登录：`POST /auth/password-login` 或 GitHub OAuth → 返回 `{access_token, expire_at}`。
- `access_token` 是 HS256 JWT，payload = `{sub: account_id, iss: "llmops", exp}`，有效期 30 天；服务端不保存会话，纯无状态校验签名与过期。
- **多端登录**：同一账号可在多台设备同时登录，各自持有独立 token；退出登录只清本端登录态，不影响其它端（30 天内 token 仍有效，要强制全端失效只能换 `JWT_SECRET_KEY`）。
- `Authorization: Bearer <token>` 为主，`?token=` 仅给 EventSource（SSE）兜底。

## 六、聊天链路（与 Hub 的协作）

| 方向 | 接口 | 说明 |
|---|---|---|
| 浏览器 → API | `POST /chat/send` | 校验 agent/conversation 归属后转发 `POST http://hub:8090/send`（3 秒超时） |
| API → Hub | `POST /send`（内网 HTTP） | 带 `X-Internal-Token`；Hub 未就绪返回 503，API 转成「智能体连接未就绪，请稍后重试」 |
| Hub → Redis | `PUBLISH stream:<account_id>` | API 的 SSE 订阅该频道 |
| API → 浏览器 | `GET /chat/stream` | `text/event-stream`，一账号一条流，空闲 20 秒发 `: ping` |
| Hub → API | `POST /internal/messages` | 只处理 `done=true` 的帧，按 `message_id` 幂等落库 |

## 七、数据模型（核心表）

| 表 | 关键字段 | 说明 |
|---|---|---|
| `account` | `id, email, name, password, password_salt` | 密码 PBKDF2-HMAC-SHA256 / 10000 轮 |
| `server` | `id, gateway_url, gateway_key` | WS 网关配置 |
| `agent` | `id, account_id, name, bot_id, peer_id, gateway_id, status` | `peer_id` 唯一；`gateway_id` 指向 `server` |
| `conversation` | `id, agent_id, account_id, thread_id, name` | 唯一约束 `(account_id, thread_id)` |
| `message` | `id, conversation_id, account_id, message_id, message_role, message_content, message_status, message_info, seq` | `message_id` 为外部幂等键；`status` 0 生成中 / 1 完成 |

时间列统一存 UTC 字面值，接口输出秒级时间戳，前端按本地时区展示。

## 八、本地启动

```bash
cd api
cp .env.example .env          # 填 SQLALCHEMY_DATABASE_URI / REDIS_* / JWT_SECRET_KEY / INTERNAL_TOKEN
.venv/bin/flask run --port 5001 --host 127.0.0.1
```

生产用 `docker compose`（见仓库根 `docker/docker-compose.yaml`），gunicorn 并发由 `SERVER_WORKER_AMOUNT` / `SERVER_THREAD_AMOUNT` 控制。

## 九、相关文档

- [API 接口文档](docs/HermesMate-Api文档.md)
- [Hub 技术架构与接口](../hub/README.md)
- [插件总览](../plugin/README.md)
