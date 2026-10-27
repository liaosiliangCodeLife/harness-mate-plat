# DSH 插件（HarnessMate）

把 DSH（DeepSeek Harness）接入 HarnessMate 平台：手机/浏览器直接与 DSH 本机 Agent 对话，支持流式回复、思考过程、文件收发。

版本：`0.2.0`（`package.json`）｜协议：沿 `../hermes/hermes_channel_protocol.md v0.5.2`

---

## 一、架构

DSH 是 Cordis 插件体系，插件通过两个钩子与宿主交互，**自己维护一条到 WS 网关的连接**：

```
HarnessMate 平台 ──HTTP/SSE──> Flask API ──HTTP──> Hub ──WS──> WS 网关
                                                                  │ P2P（to = botId）
                                                                  ▼
                                                   ┌──────────────────────────────┐
                                                   │  DSH 插件 index.js            │
                                                   │  ├ WS 客户端（JWT：botId）    │
                                                   │  ├ 收 message → followup()    │
                                                   │  └ assistant-stream → reply   │
                                                   └──────────────┬───────────────┘
                                                                  ▼
                                                      DSH Agent 运行时（ctx 服务）
```

**上行（平台 → DSH）**
```
WS 收到 {type:'message'}
  → 解析 account_id / thread_id / text / 文件
  → replyTargets.set(`${accountId}:${threadId}`, from)   // 记住回给谁
  → enqueueThreadTask(threadKey, ...)                    // 同一 thread 串行，避免并发打架
  → agent.followup(createUserMessage({ content:[{type:'text',text}], source:{kind:'user'} }))
```

**下行（DSH → 平台）**
```
ctx.on('agent/assistant-stream', ({agent, frame}))
  ├ text-delta      → makeStream() 累积，按 flushIntervalMs / flushChars 分片发 delta=true
  ├ reasoning-delta → forwardReasoning=true 时才发 reasoning 字段
  ├ block-start     → 标记新一轮回复，生成新的 message_id
  └ tool-call-delta → 可选，转成提示文本
最后 → 发 done=true 帧（含完整文本/文件）
```

## 二、事件与帧映射

| DSH 事件 | 平台帧字段 | 说明 |
|---|---|---|
| `text-delta` | `text` + `delta:true` | 正文增量，`flushIntervalMs=700` 或 `flushChars=1200` 触发一次发送 |
| `reasoning-delta` | `reasoning` | 默认不发，`forwardReasoning: true` 才带 |
| `block-start` | 新 `message_id` | 一条新回复的开始 |
| 结束 | `done:true` | 最后一次带完整文本 + 文件字段 |
| `ask_user_question` | 文本回填 | 平台下一条文本消息优先作为该问题的答案注入，不进对话队列 |

## 三、与 Hermes 插件的差异

| | Hermes 插件 | DSH 插件 |
|---|---|---|
| 接入方式 | 实现 Hermes channel 接口（`send_message` / `edit_message`） | Cordis 插件：`agent.followup()` 注入 + `ctx.on('agent/assistant-stream')` 订阅 |
| 会话隔离 | Hermes 自己按 chat_id 建会话 | 插件按 `thread_id` 建串行队列（`enqueueThreadTask`），并持久化状态（`saveState`） |
| 流式节流 | Hermes 侧控制 | 插件侧控制（`flushIntervalMs` / `flushChars`） |
| 单条长度上限 | Hermes 侧控制 | `maxReplyChars = 4000`，超出截断 |
| 文件 | 上传到平台 COS | 同样上传 `/api/open-api/upload-file`，普通文件 ≤16MB、音视频 ≤1GB、每轮最多 4 个 |
| **`account_id`** | 来自 `chat_id`（真实账号 uuid） | **优先用入站帧的 `account_id`，配置 `accountId` 仅兜底** |

## 四、配置（`cordis.patch.yml`）

| 配置项 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `gatewayUrl` | 是 | — | 形如 `wss://ws-agent.alltman.com:1443/ws` |
| `botId` | 是 | — | 智能体在网关上的身份（`bt-` 前缀），**不要复用 Hermes 的** |
| `botKey` | 是 | — | 签 JWT 的 HMAC 密钥，必须等于网关 `JWT_SECRET` |
| `accountId` | 否（建议填） | `dsh-account` | 业务身份兜底；入站帧缺 `account_id` 时才用，仍建议填真实账号 uuid |
| `dmPolicy` | 否 | `open` | `open` / `allowlist` / `disabled` |
| `allowFrom` | 否 | `[]` | `allowlist` 模式下允许的 peer id |
| `approvalTimeoutMs` | 否 | `300000` | 审批超时按拒绝处理 |
| `typingThrottleMs` | 否 | `8000` | 思考状态节流 |
| `flushIntervalMs` | 否 | `700` | 流式分片间隔 |
| `flushChars` | 否 | `1200` | 累积多少字符强制发一帧 |
| `maxReplyChars` | 否 | `4000` | 单条回复上限 |
| `forwardReasoning` | 否 | `false` | 是否把推理过程发到平台 |

### `accountId` 仅作兜底

插件出站已优先使用入站帧里的 `account_id`（`sendReply` 第 4 参数）。配置项 `accountId` 只在入站帧没有该字段时兜底。Hub 按帧里的 `account_id` 路由：

```
Hub 收到 reply → RouteOf(frame) 取 account_id → PUBLISH stream:<account_id>
前端订阅                                     → stream:<真实账号 uuid>
```

仍建议把配置填成平台真实账号 uuid：万一入站缺字段，不会落到示例值 `dsh-account`（发到错误频道，前端收不到）。

## 五、安装与排障

安装见 [`INSTALL.md`](INSTALL.md)。

| 症状 | 原因 | 处理 |
|---|---|---|
| 插件不连接 | `gatewayUrl` / `botId` / `botKey` 任一为空 | 补齐三项，重载 DSH |
| 401 | `botKey` 与网关 `JWT_SECRET` 不一致 | 对齐密钥 |
| 平台收不到回复 | 出站 `account_id` 与前端订阅不一致（旧版恒用配置；或入站缺字段且配置是示例值） | 升级到 ≥0.2.2；配置仍建议填真实账号 uuid |
| 消息不触发回复 | `dmPolicy=allowlist` 且 peer 不在 `allowFrom` | 加入 Hub 的 `peer_id` |
| 重复回复 | 同一 `msg_id` 重复投递 | 插件已按 `msg_id` 去重（最近 1000 条），检查是否两个实例同时连 |
| 连接反复断 | 同一 `botId` 多实例 | 网关只允许一条连接 |
