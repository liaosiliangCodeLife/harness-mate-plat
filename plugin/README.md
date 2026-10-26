# HarnessMate 插件

把本机跑的智能体（Hermes Agent / DSH）接到 HarnessMate 平台，让手机或浏览器能直接跟它对话：消息、流式回复、思考过程、文件上传下载全打通。

平台侧仓库：<https://github.com/liaosiliangCodeLife/harness-mate-plat>

---

## 目录

```
plugin/
├── hermes/                 Hermes Agent 插件（Python，platform adapter）
│   ├── README.md           架构与关键设计
│   ├── INSTALL.md          安装步骤
│   ├── AGENTS.md           给 Agent 读的行为约定
│   ├── adapter.py          主适配器（WS 连接 / 收发帧 / 流式）
│   ├── app_chat.py         平台侧 chat 逻辑封装
│   ├── common.py           协议工具（帧解析、reasoning、id 规则）
│   ├── file_upload.py      文件上传到平台 COS
│   └── hermes_channel_protocol.md   通道协议规范
└── dsh/                    DSH（DeepSeek Harness）插件（Node，Cordis 插件）
    ├── README.md           架构与关键设计
    ├── INSTALL.md          安装步骤
    ├── index.js            插件实现（926 行）
    ├── cordis.patch.yml    配置片段
    └── install.sh / .ps1   安装脚本
```

---

## 一、两种实现，一套协议

两个插件是**同一份通道协议的两个客户端实现**，在网关眼里没有区别：

| | Hermes 插件 | DSH 插件 |
|---|---|---|
| 语言 | Python（asyncio + websockets） | Node（ESM，无第三方 WS 库依赖） |
| 形态 | Hermes `kind: platform` 适配器 | DSH/Cordis 插件（`apply(ctx, config)`） |
| 接入方式 | 实现 Hermes channel 接口 | 订阅 `ctx.on('agent/assistant-stream')` + `agent.followup()` 注入 |
| 连接身份 | `bot_id`（`bt-` 前缀） | `botId` |
| 鉴权 | HS256 JWT，key = `bot_key` | HS256 JWT，key = `botKey` |
| 帧格式 | 见 `hermes_channel_protocol.md` | 同左 |
| 流式 | `delta=true` 多帧 + 末帧 `done=true` | 同左 |
| 保活 | 应用层 ping | 同左 |

---

## 二、整体架构

```
手机 / 浏览器
      │ HTTPS + SSE（按账号，一条流承载全部会话）
      ▼
   Flask API ──HTTP──> Hub（Go，按 agent 一条常连 WS）──WS──> WS 网关
                                                              │  P2P（按 ws_session_id 点对点）
                                                              ▼
                                             ┌────────────────┴────────────────┐
                                             ▼                                 ▼
                                    Hermes 插件（bot_id=X）          DSH 插件（botId=Y）
```

三层要点：

1. **前端只跟 API 说话**，不知道网关和 Hub 的存在。发消息 `POST /chat/send`，收消息走 `GET /chat/stream`（SSE）。
2. **Hub 扮演「一个前端设备」**：它用 `agent.peer_id` 作身份连网关，把上行帧发给 `agent.bot_id`，把收到的下行帧按 `account_id + thread_id` 发布到 Redis 频道。
3. **插件才是 bot 侧**：插件用 `bot_id/botKey` 自签 JWT 直连网关，发 `type=reply` 的帧，`to` 指向发来消息的那个 peer。

---

## 三、帧协议速查

上行业务信封（Hub → 网关 → 插件）：

```json
{
  "to": "bt-xxx",
  "data": {
    "type": "message",
    "account_id": "<uuid>",
    "thread_id": "td-xxx",
    "from_device": "pr-xxx",
    "data": { "type": "message", "text": "你好" }
  }
}
```

下行回复（插件 → 网关 → Hub）：

```json
{
  "to": "pr-xxx",
  "data": {
    "type": "reply",
    "account_id": "<uuid>",
    "thread_id": "td-xxx",
    "data": {
      "text": "增量或完整文本",
      "message_id": "m1",
      "delta": true,
      "done": false,
      "reasoning": "可选，思考过程",
      "url": "可选，文件下载地址",
      "file_name": "可选",
      "media_type": "可选：image/video/audio/file"
    }
  }
}
```

完整规范见 `hermes/hermes_channel_protocol.md` 与平台仓库 `gateway/ws_gateway_protocol.md`。

---

## 四、安装

- Hermes：见 [`hermes/INSTALL.md`](hermes/INSTALL.md)
- DSH：见 [`dsh/INSTALL.md`](dsh/INSTALL.md)

共同点：

1. 在平台「个人空间 → 创建智能体」拿到 `bot_id` + `bot_key`（**每个客户端各建一个，不要复用**）；
2. 填网关地址（形如 `wss://ws-agent.alltman.com:1443/ws`）；
3. 重启对应运行时（Hermes 需重启 gateway；DSH 需重载插件）。

---

## 五、排障入口

| 症状 | 先看哪里 |
|---|---|
| 平台发消息，Agent 没收到 | 插件日志有没有 `peer allowed` / 收到 message 帧；`dm_policy` 是否需要 allowlist |
| Agent 回了，平台不显示 | 回复帧的 `account_id`/`thread_id` 是否与平台会话一致 |
| 连接反复断开 | 网关同一 `ws_session_id` 只允许一条连接，检查是否重复启动 |
| Hermes 重启后主动推送失败 | `_reply_targets` 是内存表，重启后为空，需先收到一条消息才能重建映射 |
| 上传文件报 401/session_id 为空 | 检查插件版本与 `session_id` 传参（见 hermes/README.md） |
