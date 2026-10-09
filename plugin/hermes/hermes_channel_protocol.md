# Hermes Channel 协议规范（harness_mate）

> 项目路径：`agent_body/agents_plugin/hermes_plugin/`  
> 协议版本：0.5.2  
> 依赖网关协议：[ws_gateway_protocol.md](../../ws_gateway/ws_gateway_protocol.md) v0.5+  
> 最后更新：2026-07-02

---

## 1. 设计原则

Hermes Channel 是 **harness_mate 平台插件**在 WS Gateway 之上约定的业务协议，用于 **对端客户端（Peer）** 与 **Hermes Agent** 之间的双向通信。

- **路由层**：由网关按 `ws_session_id` 点对点转发（见网关协议）
- **业务层**：由本协议在 `data` 负载内约定字段语义
- **路由 ID 与业务 ID 必须分离**：`from_device` 是逻辑设备标识，**不得**当作 `ws_session_id` 使用

```plaintext
┌─────────────┐   {to, data}    ┌─────────────┐   {from, to, data}   ┌─────────────┐
│    Peer     │ ──────────────► │  WS Gateway │ ───────────────────► │   Hermes    │
│ ws_session  │                 │  (透明转发)  │                      │ ws_session  │
└─────────────┘                 └─────────────┘                      └─────────────┘
```

---

## 2. 角色与 ID 字段

### 2.1 角色

| 角色 | 说明 |
|------|------|
| **Peer** | 对端客户端（手机 App、桌面客户端等） |
| **Hermes** | 运行 harness_mate 插件的 Hermes Agent |
| **Gateway** | WS Gateway，仅负责鉴权与按 `ws_session_id` 转发 |

### 2.2 ID 字段总览

共 **6 种 ID**，其中 **5 个必传/必配**，**1 个可选**。

| # | 字段名 | 层级 | 传递方 | 必填 | 说明 |
|---|--------|------|--------|------|------|
| 1 | Hermes `ws_session_id` | 路由 | Hermes 连接配置 | ✅ | Hermes 本端会话 ID（配置项 `bot_id`） |
| 2 | Peer `ws_session_id` | 路由 | Peer 连接 JWT | ✅ | Peer 本端会话 ID；网关注入为 `from` |
| 3 | `to` | 路由 | 发送方信封 | ✅ | 目标 `ws_session_id` |
| 4 | `account_id` | 业务 | 业务 payload | ✅ | Hermes 账号标识 |
| 5 | `thread_id` | 业务 | 业务 payload | 建议 | 会话线程，隔离多轮上下文 |
| 6 | `from_device` | 业务 | 业务 payload | 建议 | 逻辑设备标识，仅业务语义 |
| 7 | `msg_id` / `message_id` | 业务 | 业务 payload | ❌ | 入站消息去重（可选） |

### 2.3 两层 ID 对照

```plaintext
路由层（网关识别）
├── Hermes ws_session_id   ← 配置 bot_id
├── Peer ws_session_id     ← 连接 JWT；网关注入 from
└── to                     ← 信封目标 ws_session_id

业务层（Hermes 插件识别）
├── account_id             ← 账号 / chat_id
├── thread_id              ← 会话线程
└── from_device            ← 逻辑设备（不参与路由）
```

### 2.4 自动注入 / 自动生成字段

| 字段 | 来源 | 说明 |
|------|------|------|
| `from` | 网关注入 | 发送方 `ws_session_id`；Hermes 回复时用作路由目标 |
| 回复 `message_id` | Hermes 插件生成 | UUID；流式多帧共用 |

---

## 3. 连接与鉴权

### 3.1 Hermes 侧配置

| 配置项 | 环境变量 | 兼容别名 | 说明 |
|--------|----------|----------|------|
| `bot_id` | `HARNESS_MATE_BOT_ID` | `ws_session_id` | 本端 `ws_session_id` |
| `bot_key` | `HARNESS_MATE_BOT_KEY` | `jwt_secret` | JWT HMAC 密钥，与网关 `JWT_SECRET` 一致 |

**可选访问控制：**

| 配置项 | 环境变量 | 说明 |
|--------|----------|------|
| `dm_policy` | `HARNESS_MATE_DM_POLICY` | `open`（默认）/ `allowlist` / `disabled` |
| `allow_from` | `HARNESS_MATE_ALLOWED_PEERS` | 允许通信的对端 `ws_session_id` 白名单 |
| — | `HARNESS_MATE_ALLOW_ALL_DEVICES` | 开发用，允许所有对端 |

> 白名单匹配的是对端 **`ws_session_id`**（网关 `from`），不是 `from_device`。

### 3.2 Peer 侧连接

Peer 通过网关统一端点连接：

```text
ws://<gateway_host>:<gateway_port>/ws?token=<jwt>
```

JWT Claims：

```json
{
  "ws_session_id": "<peer-ws_session_id>",
  "exp": 1735689600,
  "iat": 1735603200
}
```

### 3.3 Hermes 侧连接 JWT

```json
{
  "ws_session_id": "<hermes-bot_id>",
  "exp": 1735689600,
  "iat": 1735603200
}
```

签名算法：`HS256`，密钥为 `bot_key`（与网关 `JWT_SECRET` 一致）。

---

## 4. 网关消息信封

本协议复用网关标准信封，详见 [ws_gateway_protocol.md](../../ws_gateway/ws_gateway_protocol.md)。

### 4.1 发送方 → 网关

```json
{
  "to": "<目标-ws_session_id>",
  "data": { }
}
```

### 4.2 网关 → 接收方

```json
{
  "from": "<发送方-ws_session_id>",
  "to": "<本端-ws_session_id>",
  "data": { }
}
```

---

## 5. 业务消息：Peer → Hermes（`type: message`）

### 5.1 Peer 发送

```json
{
  "to": "<hermes-ws_session_id>",
  "data": {
    "type": "message",
    "account_id": "<account_id>",
    "thread_id": "<thread_id>",
    "from_device": "<from_device>",
    "data": {
      "type": "message",
      "text": "<用户消息正文>"
    }
  }
}
```

### 5.2 Hermes 收到（网关注入 `from`）

```json
{
  "from": "<peer-ws_session_id>",
  "to": "<hermes-ws_session_id>",
  "data": {
    "type": "message",
    "account_id": "<account_id>",
    "thread_id": "<thread_id>",
    "from_device": "<from_device>",
    "data": {
      "type": "message",
      "text": "<用户消息正文>"
    }
  }
}
```

### 5.3 字段说明

| 字段路径 | 必填 | 说明 |
|----------|------|------|
| `to` | ✅ | 目标 Hermes 的 `ws_session_id`（即 `bot_id`） |
| `from` | ✅ | 由网关注入，Peer 的 `ws_session_id` |
| `data.type` | ✅ | 固定为 `"message"` |
| `data.account_id` | ✅ | Hermes 账号标识 |
| `data.thread_id` | 建议 | 会话线程 ID |
| `data.from_device` | 建议 | 逻辑设备 ID，映射为业务 `user_id` |
| `data.data.type` | ✅ | 固定为 `"message"` |
| `data.data.text` | 文本消息必填 | 用户消息正文。仅发送文件时可以只传 `url` |
| `data.data.url` | 文件消息必填 | 已通过 `POST /open-api/upload-file` 得到的可访问地址，也接受 `file_url` |
| `data.data.file_name` | ❌ | 文件名 |
| `data.data.media_type` | ❌ | `image` 或 `file`；缺省时按扩展名判断 |
| `data.msg_id` | ❌ | 消息去重 ID（可选） |
| `data.data.message_id` | ❌ | 消息去重 ID（可选，与 `msg_id` 二选一） |

---

## 6. 业务消息：Hermes → Peer（`type: reply`）

### 6.1 Hermes 发送

```json
{
  "to": "<peer-ws_session_id>",
  "data": {
    "type": "reply",
    "account_id": "<account_id>",
    "thread_id": "<thread_id>",
    "data": {
      "text": "<回复正文>",
      "message_id": "<uuid>",
      "delta": true,
      "done": true
    }
  }
}
```

### 6.2 Peer 收到（网关注入 `from`）

```json
{
  "from": "<hermes-ws_session_id>",
  "to": "<peer-ws_session_id>",
  "data": {
    "type": "reply",
    "account_id": "<account_id>",
    "thread_id": "<thread_id>",
    "data": {
      "text": "<回复正文>",
      "message_id": "<uuid>",
      "delta": true,
      "done": true
    }
  }
}
```

### 6.3 字段说明

**data 外层：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `to` | ✅ | 目标 Peer 的 `ws_session_id`（等于入站 `from`） |
| `data.type` | ✅ | 固定为 `"reply"` |
| `data.account_id` | ✅ | 与入站 message 一致 |
| `data.thread_id` | 建议 | 与入站 message 一致 |

**data.data 内层（reply 负载）：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `text` | ✅ | 回复正文（最大 4000 字符） |
| `message_id` | ✅ | 消息 ID；流式多帧共用 |
| `delta` | 流式时 | `true` 表示增量帧 |
| `done` | 流式结束时 | `true` 表示最终帧 |
| `status` | ❌ | `"thinking"` 表示思考中 |
| `reasoning` | ❌ | 思考过程文本（可选） |
| `url` | 文件回复时 | 文件可访问地址。本地文件先经 `POST /open-api/upload-file` 上传，`session_id` 使用当前对端 `ws_session_id` |
| `file_name` | 文件回复时 | 文件名 |
| `media_type` | 文件回复时 | `image`、`file`、`audio` 或 `video`。音频扩展名：mp3、wav、m4a、aac、flac、ogg、oga、opus、amr、wma、aiff、mka；视频扩展名：mp4、mov、m4v、avi、mkv、webm、flv、wmv、mpeg、mpg、ts、3gp。普通文件（图片、文档）最大 16MB，音频和视频最大 1024MB |

### 6.4 思考中状态（typing）

Hermes 在生成回复前可能发送：

```json
{
  "to": "<peer-ws_session_id>",
  "data": {
    "type": "reply",
    "account_id": "<account_id>",
    "thread_id": "<thread_id>",
    "data": {
      "status": "thinking",
      "text": "思考中..."
    }
  }
}
```

---

## 7. 回复路由规则

Hermes 插件收到 Peer 的 `message` 后，须将入站 `from` 记录为回复目标。回复时信封 `to` **必须**等于 Peer 的 `ws_session_id`（即入站 `from`），**不得**使用 `from_device`。

路由目标解析优先级：

1. 同 `(account_id, thread_id)` 下记录的入站 `from`
2. 同 `account_id` 下最近一次入站 `from`
3. 最近一次通信对端的 `from`
4. `from_device` → `ws_session_id` 的映射（仅作备用，须基于入站 `from` 建立）
5. 显式指定的 `to_ws_session` / `to`（metadata）

---

## 8. 完整对话时序

```plaintext
Peer (<peer-ws_session_id>)        WS Gateway           Hermes (<hermes-ws_session_id>)
        │                                │                                │
        │── WS Connect /ws?token=... ───►│                                │
        │◄──────── 101 Switching ────────│                                │
        │                                │◄── WS Connect /ws?token=... ───│
        │                                │────── 101 Switching ──────────►│
        │                                │                                │
        │── {to:hermes, data:message} ─►│── {from:peer, to:hermes, data} ►│
        │                                │                                │
        │◄─ {from:hermes, to:peer, reply}◄│◄── {to:peer, data:reply} ──────│
        │                                │                                │
```

---

## 9. 错误与丢弃行为

### 9.1 网关层

| 场景 | 行为 |
|------|------|
| `to` 缺失 | 记录 error，不转发 |
| `to` 等于自身 session | 丢弃 |
| 目标 session 离线 | 丢弃，日志 `target is offline` |
| 目标在其他 gateway 实例 | 丢弃 |
| JWT 无效 | HTTP 401，拒绝连接 |

### 9.2 Hermes 插件层

| 场景 | 行为 |
|------|------|
| 入站缺少 `from` | 忽略 |
| `data.type` 非 `message` | 忽略 |
| 入站无文本内容 | 忽略 |
| 对端不在白名单 | 忽略（`dm_policy=allowlist`） |
| 重复 `msg_id` | 忽略 |
| 回复 `to` 使用了 `from_device` | 网关判定目标离线，消息丢弃 |

### 9.3 常见路由错误

| 错误 | 现象 |
|------|------|
| Peer / Hermes `ws_session_id` 拼写不一致 | `target is offline` |
| 回复 `to` = `from_device` 而非 `from` | `target is offline` |
| Peer 未保持 WebSocket 连接 | `target is offline` |

---

## 10. 协议常量

| 名称 | 值 | 说明 |
|------|-----|------|
| 业务类型 `message` | `"message"` | Peer → Hermes 入站 |
| 业务类型 `reply` | `"reply"` | Hermes → Peer 出站 |
| 最大回复长度 | `4000` | 字符数上限 |
| 客户端 Ping 间隔 | `50s` | 建议值，与网关读超时配合 |
| 读超时 | `90s` | 网关侧，无活动则断开 |
| 思考状态节流 | `8s` | 同一对端同线程最小发送间隔 |

---

## 11. 最小字段清单

一次完整对话，各端最少需提供：

**Hermes 侧（配置）：**

```plaintext
bot_id   = <hermes-ws_session_id>
bot_key  = <与网关 JWT_SECRET 一致>
```

**Peer 侧（连接 + 每条 message）：**

```plaintext
ws_session_id  = <peer-ws_session_id>    # JWT；网关注入 from
to             = <hermes-ws_session_id>   # 信封目标
account_id     = <account_id>
thread_id      = <thread_id>             # 建议
from_device    = <from_device>           # 建议；不参与路由
```

**Hermes 回复（每条 reply）：**

```plaintext
to             = <peer-ws_session_id>    # 必须等于入站 from
account_id     = <与入站一致>
thread_id      = <与入站一致>
data.text      = <回复正文>
data.message_id = <uuid>
```

---

## 12. 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.5.3 | 2026-10-07 | Hermes 发送本地图片/文档时先调用免授权上传，reply 携带 `url`；入站 message 可带 `url` |
| 0.5.2 | 2026-07-02 | 明确路由层与业务层 ID 分离；回复路由须使用入站 `from` |
| 0.5.1 | 2026-07-02 | Hermes 配置简化为 `bot_id` + `bot_key` |
| 0.5.0 | 2026-07-02 | 统一 `ws_session_id` 点对点模型 |

---

## 13. 相关文档

| 文档 | 说明 |
|------|------|
| [ws_gateway_protocol.md](../../ws_gateway/ws_gateway_protocol.md) | 网关传输层协议 |
| `plugin.yaml` | 插件环境变量与配置项声明 |
