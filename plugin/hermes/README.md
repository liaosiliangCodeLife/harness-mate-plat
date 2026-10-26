# Hermes 插件（HarnessMate）

Hermes Agent 的平台适配器：把本机 Hermes 接到 HarnessMate 平台，手机/浏览器即可与它对话。

版本：`0.5.5`（`plugin.yaml`）｜协议：`hermes_channel_protocol.md`

---

## 一、架构

```
HarnessMate 平台 ──HTTP/SSE──> Flask API ──HTTP──> Hub ──WS──> WS 网关
                                                                  │ P2P
                                                                  ▼
                                                      ┌────────────────────┐
                                                      │  Hermes 插件        │
                                                      │  adapter.py         │
                                                      │   ├ 自签 JWT 连网关  │
                                                      │   ├ 收 message 帧    │
                                                      │   └ 调 Hermes 通道   │
                                                      └─────────┬──────────┘
                                                                ▼
                                                     Hermes Agent（本机模型/tools）
```

要点：

- 插件是 **WebSocket 客户端**，用 `bot_id` + `bot_key`（HS256）签 JWT 连 `gateway_url`，一条常连不断（重连退避 1s/2s/5s，封顶 10s）。
- 平台消息进来 → 插件转成 Hermes 的用户输入；Hermes 产出的文本/思考/文件 → 插件转成 `type=reply` 帧发回网关。
- 流式靠 `delta=true` 多帧 + 末帧 `done=true`，同一个 `message_id`。

## 二、文件职责

| 文件 | 行数 | 作用 |
|---|---|---|
| `adapter.py` | 1454 | 主适配器：WS 连接与重连、帧收发、流式回复、peer 白名单、文件收发 |
| `app_chat.py` | 607 | 平台侧 chat 逻辑：把平台会话映射到 Hermes 会话、消息落位 |
| `common.py` | 294 | 协议工具：帧解析、reasoning 提取、id 规则、上传辅助 |
| `file_upload.py` | 440 | 文件上传到平台 COS（`/open-api/upload-file`） |

## 三、关键设计

**1. `_reply_targets` 是内存表**
键是 `(account_id, thread_id)`，值是 peer 的 `ws_session_id`。Hermes 重启后表为空——此时主动推送（cron 消息）会失败，必须等用户先发一条消息重建映射。排障时先想到这里。

**2. peer 白名单**
`dm_policy` = `open` / `allowlist` / `disabled`；`allowlist` 时只有 `HARNESS_MATE_ALLOWED_PEERS` 里的 peer 能发消息。Hub 的 `peer_id` 必须在这个表里（否则 Hub 转发过来的消息会被丢弃）。

**3. 去重指纹**
同一条 `message_id` 的连续相同内容只发一次（`_reply_fingerprints`），避免流式编辑重复推帧。

**4. 文件**
- 上传：走平台 `/open-api/upload-file`，multipart 同时带 `session_id` 与 `thread_id`（新版接口必需 `session_id`，值取自会话的 `ws_session_id`）；
- 下载：平台发来的 `url` 先落到本地临时目录，再作为附件交给 Hermes。

**5. 打字状态节流**
`typing` 帧按 8 秒节流，避免刷屏。

## 四、配置

`plugin.yaml` 声明的环境变量：

| 变量 | 必填 | 说明 |
|---|---|---|
| `HARNESS_MATE_BOT_ID` | 是 | 平台创建智能体时拿到的 `bot_id`（`bt-` 前缀） |
| `HARNESS_MATE_BOT_KEY` | 是 | 签 JWT 的 HMAC 密钥，必须等于网关的 `JWT_SECRET` |
| `HARNESS_MATE_ALLOWED_PEERS` | 否 | 允许的 peer id，逗号分隔 |
| `HARNESS_MATE_ALLOW_ALL_DEVICES` | 否 | 开发用，放开全部 peer（生产别开） |
| `HARNESS_MATE_DM_POLICY` | 否 | `open`（默认）/`allowlist`/`disabled` |
| `HARNESS_MATE_UPLOAD_URL` | 否 | 上传接口地址，默认 `https://harness.alltman.com/api/open-api/upload-file` |

网关地址在 `adapter.py` 顶部常量 `WS_GATEWAY_WS_URL`（形如 `wss://ws-agent.alltman.com:1443/ws`）。

## 五、安装与排障

安装见 [`INSTALL.md`](INSTALL.md)，Agent 行为约定见 [`AGENTS.md`](AGENTS.md)。

常见问题：

| 症状 | 原因 | 处理 |
|---|---|---|
| 平台发消息没反应 | `dm_policy=allowlist` 且 Hub 的 peer 不在名单 | 把 `agent.peer_id` 加进 `HARNESS_MATE_ALLOWED_PEERS` |
| 回复发不出去 | WS 未连通 / JWT 过期 | 看插件日志的 `send failed`，检查 `bot_key` 与网关 `JWT_SECRET` |
| 重启后 cron 推送失败 | `_reply_targets` 空 | 让用户先发一条消息 |
| 上传图片报 `session_id 不能为空` | 插件版本 < 0.5.5 或没传 `session_id` | 升到 0.5.5，确认 `conversation.ws_session_id` 已注入 |
| 连接被踢 | 同一个 `bot_id` 起了两个实例 | 网关同一 `ws_session_id` 只允许一条连接 |
