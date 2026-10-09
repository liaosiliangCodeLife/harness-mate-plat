# WS Gateway 协议规范

> 项目路径：`agent_body/ws_gateway/`  
> 协议版本：0.5.0  
> 最后更新：2026-07-02

---

## 1. 设计原则

WS Gateway 是 **纯传输层** WebSocket 中继，不包含业务语义。

- 每个连接持有全局唯一的 **`ws_session_id`**
- 网关 **不解析** `data` 内任何业务字段
- 网关职责：**鉴权、注册在线、按 `to` 点对点转发、心跳保活**
- 业务协议由上层客户端在 `data` 内自行约定

```plaintext
┌─────────────┐   {to, data}    ┌─────────────┐   {from, to, data}   ┌─────────────┐
│  Session A  │ ──────────────► │  WS Gateway │ ───────────────────► │  Session B  │
│ ws_session  │                 │  (透明转发)  │                      │ ws_session  │
└─────────────┘                 └─────────────┘                      └─────────────┘
```

---

## 2. 术语

| 术语 | 说明 |
|------|------|
| **Session** | 一个已鉴权并保持 WebSocket 连接的客户端 |
| **ws_session_id** | Session 的全局唯一标识，用于路由 |
| **Instance** | 网关进程实例 ID，写入 Redis 标识 Session 所在节点 |
| **Envelope** | 网关层消息信封 `{to, data}` 或 `{from, to, data}` |

---

## 3. 连接

### 3.1 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/ws?token=<jwt>` | WebSocket 升级（唯一业务端点） |
| `GET` | `/healthz` | 健康检查，响应体 `ok` |

连接 URL 格式：

```text
ws://<host>:<port>/ws?token=<jwt>
```

生产环境建议在反向代理后暴露为 `wss://`。

### 3.2 JWT 鉴权

握手阶段通过 Query 参数 `token` 传递 JWT。网关使用共享密钥 `JWT_SECRET`，算法 **HMAC-SHA256** 验签。

**Claims 结构：**

```json
{
  "ws_session_id": "<本端-ws_session_id>",
  "exp": 1735689600,
  "iat": 1735603200
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `ws_session_id` | 是* | 本连接唯一标识，用于路由与在线注册 |
| `sub` | 否 | 当 `ws_session_id` 为空时，fallback 为 `sub` |
| `exp` | 推荐 | JWT 过期时间（Unix 秒） |
| `iat` | 推荐 | JWT 签发时间（Unix 秒） |

> *`ws_session_id` 与 `sub` 至少有一个非空。

**鉴权失败：** HTTP `401`，拒绝 WebSocket 升级。

### 3.3 连接互斥

同一 `ws_session_id` 重复连接时，**新连接替换旧连接**（旧连接被关闭）。

### 3.4 在线注册

连接成功后，网关写入 Redis：

```text
SET ws:session:{ws_session_id} {instance_id}
```

连接断开时删除对应 Key。

---

## 4. 消息信封

所有消息均为 **JSON 文本帧**（WebSocket TextMessage）。

### 4.1 客户端 → 网关（发送）

```json
{
  "to": "<目标-ws_session_id>",
  "data": { }
}
```

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `to` | ✅ | string | 目标 Session ID；不可为空；不可等于本端 `ws_session_id` |
| `data` | ❌ | any JSON | 任意 JSON 值；网关原样透传，不做解析或修改 |

### 4.2 网关 → 客户端（转发）

```json
{
  "from": "<发送方-ws_session_id>",
  "to": "<本端-ws_session_id>",
  "data": { }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `from` | string | 由网关注入，等于发送方 `ws_session_id` |
| `to` | string | 与发送方原始 `to` 一致 |
| `data` | any JSON | 与发送方原始 `data` 一致，不做修改 |

---

## 5. 路由规则

收到客户端消息后，网关按以下顺序处理：

1. 解析 JSON；失败则记录 error，不影响连接
2. 读取 `to`；为空则记录 error，不转发
3. `to` 等于本端 `ws_session_id` → 丢弃，记录 warn
4. 查询 Redis：`GET ws:session:{to}`
5. Key 不存在（目标离线）→ 丢弃，记录 warn
6. 值不等于本机 `instance_id`（目标在其他网关节点）→ 丢弃，记录 warn
7. 目标在本机连接池 → 写入目标 Session 发送队列

> 当前版本 **不支持跨 Instance 转发**。

---

## 6. 心跳

| 参数 | 值 | 说明 |
|------|-----|------|
| 客户端 Ping 间隔 | 建议 **≤ 50s** | 客户端主动发送 WebSocket Ping 帧 |
| 服务端行为 | 回复 Pong | 网关不主动 Ping 客户端 |
| 读超时 | **90s** | 90s 内无任何读活动（含 Ping）则断开连接 |

客户端须保证在读超时前发送 Ping 或业务消息，以维持连接。

---

## 7. Redis

### 7.1 Session 在线映射

| Key | 类型 | 值 | 说明 |
|-----|------|-----|------|
| `ws:session:{ws_session_id}` | String | `{instance_id}` | Session 当前所在网关节点 |

| 事件 | 操作 |
|------|------|
| 连接成功 | `SET ws:session:{ws_session_id} {instance_id}` |
| 连接断开 | `DEL ws:session:{ws_session_id}` |

### 7.2 踢线（Pub/Sub）

管理面可通过 Redis 发布踢线事件，强制关闭指定 Session 的本地连接：

| Channel | 说明 |
|---------|------|
| `kick_session:{ws_session_id}` | 关闭该 Session 在本节点的 WebSocket 连接 |

---

## 8. 消息转发时序

```plaintext
Session A (<ws_session_id_A>)      WS Gateway      Session B (<ws_session_id_B>)
        │                                │                                │
        │── WS /ws?token=<jwt_A> ───────►│                                │
        │◄──────── 101 Switching ────────│                                │
        │                                │◄── WS /ws?token=<jwt_B> ───────│
        │                                │────── 101 Switching ──────────►│
        │                                │                                │
        │── {to:B, data:{...}} ─────────►│── {from:A, to:B, data:{...}} ─►│
        │                                │                                │
        │◄─ {from:B, to:A, data:{...}} ◄─│◄── {to:A, data:{...}} ─────────│
        │                                │                                │
```

---

## 9. 错误与丢弃行为

| 场景 | 网关行为 |
|------|----------|
| JWT 无效 / 过期 / 缺少 session ID | HTTP 401，拒绝升级 |
| 消息 JSON 解析失败 | 记录 error，不转发，连接保持 |
| `to` 缺失 | 记录 error，不转发 |
| `to` 等于本端 session | 丢弃，记录 warn |
| 目标 session 离线 | 丢弃，记录 warn（`target is offline`） |
| 目标在其他 gateway instance | 丢弃，记录 warn |
| 目标在本机但连接不存在 | 丢弃，记录 warn |
| 读超时（90s 无活动） | 关闭连接，清理 Redis |
| 同 `ws_session_id` 重连 | 关闭旧连接，保留新连接 |

---

## 10. 网关部署配置

| 变量 | 说明 |
|------|------|
| `WS_GATEWAY_HOST` | 监听地址 |
| `WS_GATEWAY_PORT` | 监听端口 |
| `WS_GATEWAY_INSTANCE` | 本实例 ID，写入 Redis |
| `JWT_SECRET` | JWT 验签密钥（HMAC-SHA256） |
| `REDIS_URL` | Redis 连接地址 |
| `WS_GATEWAY_LOG_DIR` | 日志目录（可选） |
| `WS_GATEWAY_LOG_LEVEL` | 日志级别（可选） |

---

## 11. 对接说明

### 11.1 客户端最小实现

1. 持有唯一 `ws_session_id`
2. 使用与网关相同的 `JWT_SECRET` 签发 JWT
3. 连接 `ws://<host>:<port>/ws?token=<jwt>`
4. 定期发送 WebSocket Ping（建议 ≤ 50s）
5. 发送消息：`{"to": "<目标-ws_session_id>", "data": <任意JSON>}`
6. 接收消息：解析 `{from, to, data}`，`from` 为发送方 `ws_session_id`

### 11.2 业务层协议

网关 **仅传输** `data` 字段，不定义其内部结构。  
上层业务协议（如 Hermes Channel）由客户端自行约定，参见：

- [hermes_channel_protocol.md](../agents_plugin/hermes_plugin/hermes/hermes_channel_protocol.md)

---

## 12. 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.5.0 | 2026-07-02 | 统一 `ws_session_id` 点对点模型；单一 `/ws` 端点；移除按 account/device 路由 |
| 0.4.0 | — | 旧版：分端点，按 account_id / device_id 路由 |
