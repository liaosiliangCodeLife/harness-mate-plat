# Hub API 文档

Hub 是平台与 WS 网关之间的常连汇聚层（Go 服务），**只监听 docker 内网**（默认 `:8090`），不对外暴露。调用方只有两个：

| 调用方 | 接口 | 用途 |
|---|---|---|
| API（Flask） | `POST /send` | 把用户的一条消息转发给指定智能体 |
| Docker / 运维 | `GET /healthz` | 容器健康检查 |

---

## 01. 鉴权

`POST /send` 必须携带服务间令牌：

```
X-Internal-Token: <INTERNAL_TOKEN>
```

令牌与 API 共享 `docker/.env` 里的 `INTERNAL_TOKEN`，**不能复用用户 access_token**——用户离线后 token 就失效了，而 Hub 恰恰要在用户离线时继续工作。

`GET /healthz` 不需要鉴权。

---

## 02. 发送消息

### 2.1 接口信息

`POST:/send`

### 2.2 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 智能体 id（uuid 字符串），作为连接池的 key：同一 agent 复用同一条上游 WS |
| `bot_id` | string | 是 | 智能体在网关上的身份（`bt-` 前缀），作为下行帧的 `to` |
| `gateway_url` | string | 是 | 已含 `/ws` 的网关地址，如 `wss://ws-agent.alltman.com:1443/ws` |
| `gateway_key` | string | 是 | 签 JWT 用的 HMAC 密钥（= 网关 `JWT_SECRET`） |
| `account_id` | string | 是 | 平台账号 id（uuid），写进业务信封，用于下行路由 |
| `thread_id` | string | 是 | 会话线程标识，写进业务信封 |
| `peer_id` | string | 否 | 上游连接身份；为空时回退 `hub-<bot_id>` |
| `text` | string | 是 | 消息正文 |

### 2.3 转发出去的帧

Hub 把请求转成网关协议信封（§4.1），发给 `bot_id`：

```json
{
  "to": "bt-MTMzNTRhOGUwY2NiN2JiZTIyNTNiM",
  "data": {
    "type": "message",
    "account_id": "bb0b708e-9d53-4166-bbcc-8b86c4839ebf",
    "thread_id": "td-1791623452452",
    "from_device": "pr-OTc1YTdiMmVhMTVmNzA3YmM2MjFjM",
    "data": {
      "type": "message",
      "text": "你好"
    }
  }
}
```

### 2.4 响应

成功：

```json
{"ok": true}
```

### 2.5 状态码

| HTTP | body | 含义 | 调用方该怎么做 |
|---|---|---|---|
| 200 | `{"ok":true}` | 网关已收下 | 正常 |
| 401 | `{"ok":false,"error":"unauthorized"}` | 令牌不匹配 | 不要重试，检查 `INTERNAL_TOKEN` |
| 400 | `{"ok":false,"error":"invalid request body"}` | body 不是 JSON 对象 | 不要重试 |
| 400 | `{"ok":false,"error":"<字段校验信息>"}` | 必填字段缺失/为空 | 不要重试 |
| 500 | `{"ok":false,"error":"marshal outbound frame failed"}` | 组帧失败 | 记录告警 |
| 503 | `{"ok":false,"error":"<连接未就绪>"}` | 上游 WS 尚未连通（首次发送会懒建连，约 0.14s） | **可以重试**，通常立刻重试一次就成功 |
| 502 | `{"ok":false,"error":"<写失败原因>"}` | 已连通但写帧失败 | 可以重试 |

---

## 03. 健康检查

### 3.1 接口信息

`GET:/healthz`

### 3.2 响应

```
HTTP/1.1 200 OK
Content-Type: text/plain

ok
```

容器 `HEALTHCHECK` 每 30 秒调用一次，失败 3 次判定 unhealthy。

---

## 04. 与 API 的重试约定

`POST /internal/messages`（由 Hub 调用 API，方向相反）有一套独立的错误约定，见 [`hub/README.md`](../README.md) 的「内部接口契约」一节。要点：

- `code == "success" && data.stored == true` → 落库成功
- `code == "success" && data.stored == false` → 会话不存在，记 warn，**不重试**
- 4xx → 不重试
- 5xx / 429 / 网络错误 → 最多重试 3 次，间隔 1 秒
