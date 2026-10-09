# `plugin/dsh/` —— 微信远程控制 DSH 方案的归档与复用评估

> 归档对象：`wechat-remote-control-完整方案.md`（微信远程控制 DSH · 完整方案与通信协议 v1.0，生成于 2026-10-09，适用 DSH Desktop `0.2.0-rc.2`）
> 归档时间：2026-10-09　维护：助理廖老师
> 评估范围：该方案与 **Hermes Agent + HarnessMate 现有栈**（`plugin/hermes/` + `gateway/`）的复用关系

---

## 0. 结论速览

| 复用层次 | 可复用度 | 说明 |
|---|---|---|
| 传输层语义（鉴权 / 路由 / 心跳 / 重连） | **高** | HarnessMate WS 网关 + `plugin/hermes/common.py` 已实现同款能力，且更完整（Redis 在线注册、连接互斥、kick 线） |
| 业务协议（流式 / 会话 / 文件） | **高** | `plugin/hermes/hermes_channel_protocol.md` 已定义 `message` / `reply`（含 `delta`/`done`/`message_id`）、`thread_id` 会话隔离、`/api/open-api/upload-file` 文件回传 |
| 插件**代码本体** | **低** | `adapter.py` 继承 Hermes 内部 API `gateway.platforms.base.BasePlatformAdapter`，跑在 Hermes 进程内、Python 宿主；DSH 是 Electron/Node 宿主，无法加载 |
| 守护进程**逻辑** | **中** | 重连退避、按会话串行、去重、ANSI 清洗、分片冲刷等逻辑在 `adapter.py` 有现成实现，**移植**（非 import）成本约 200 行 |

**一句话**：方案里的「自研 relay + 自研协议 v1.0」这一半，是现有栈里**已经有了**的东西；真正缺的只是 DSH 侧的「谁去跑 `dsh headless`」。因此有三种落地路线（见 §3），推荐 **路线 B**（DSH 守护进程 + 复用网关与通道协议），若执行器允许是 Hermes 则 **路线 A** 可直接零新协议。
> **2026-10-09 更新**：老板已确认方案 §1.2 的「已有 WebSocket 网关（含微信协议实现）」**就是 HarnessMate 网关** → 路线 C 排除，剩余缺口收敛为「微信侧 client」（见 §3.4），建议动作改见 §6。

---

## 1. 逐项对比：方案自研件 vs 现有件

| 能力 | DSH 方案怎么做 | Hermes / HarnessMate 现有件 | 复用 |
|---|---|---|---|
| 出站长连接 + 鉴权 | `hello{deviceId,token}`，relay 常量时间比对（§4.4） | JWT HS256（claim=`ws_session_id`）+ `GET /ws?token=`（`gateway/ws_gateway_protocol.md` §3） | ✅ 直接用网关 |
| 路由 | 自研 relay，★ 必须维护 `reqId → userId`（§4.6） | 网关按 `to` 点对点转发 + Redis `ws:session:{id}`（协议 §5/§7） | ✅ 免自研 |
| 连接互斥 / 踢线 | 未提 | 同 session 新连接替换旧连接；Redis Pub/Sub `kick_session:*`（§3.3/§7.2） | ✅ |
| 心跳 | 应用层 `ping` 30s，3 次无 `pong` 重连（§4.4） | WS 控制帧 Ping ≤50s / Pong + 服务端 90s 读超时（§6）；`adapter.py` 50/90 可配 | ✅ |
| 断线重连 | 指数退避 1s→60s，±50% 抖动（§4.7） | `adapter.py::_reconnect_loop` 1s→30s（`HARNESS_MATE_RECONNECT_*`） | ✅ 可移植 |
| 流式输出 | `output_chunk{reqId,seq,text}`，1200ms / 1500 字分片 | `reply{message_id,delta,done,text}`（≤4000 字符），同一 `message_id` 多帧 | ✅ 语义等价，协议已有 |
| 多轮会话 | 本地 `sessionStore` JSON + `sessionId`，隔离主键 `userId` | `account_id` + `thread_id`；平台侧 conversation 表落库（含 `ws_session_id`） | ✅ 更完整 |
| 「思考中」状态 | 无 | `reply{status:"thinking"}` + 8s 节流 | ✅ |
| 文件/图片回传 | 无 | `plugin/hermes/file_upload.py` + `POST /api/open-api/upload-file`（普通文件 16MB / 音视频 1024MB） | ✅ |
| 去重 | 明说**不防重**（§4.4 `reqId` / §9.2） | `gateway.platforms.helpers.MessageDeduplicator`（1000 条） | ✅ 可移植 |
| 取消 | **软取消**，只记日志（§4.9/§4.4） | 平台侧中断 + 流式停止语义 | ✅ |
| 多机 / 多 agent | v1 单 agent（§9.4） | 网关 Redis `instance` 契约已在（当前不支持跨实例转发，但契约在） | ✅ 契约可复用 |
| 客户端 UI | 无（微信侧自理） | `harness.alltman.com` UI（会话列表 / 流式气泡 / 音视频内联播放） | ✅ 白得 |
| 管理面 / 账号 | 无 | 平台 account 表、智能体（`bot_id`/`bot_key`）、免登录上传接口 | ✅ |

---

## 2. 方案的「插件路线」章节为何没对上

方案 §5.4 比较的是 **DSH 自己的 Cordis 插件**（`dsh-webhook` / `dsh-acp`），§10.3 又澄清 `dsh-api-gateway` 只是 DSH 内部 RPC —— 这些都与 Hermes 插件体系无关。方案全文未提及已有的 **Hermes 平台适配器插件 + WS 网关 + 平台 UI**，而这一套恰好就是它 §3「消息总线 + 转发 + 会话」部分的重实现。

换句话说：**方案把「总线/协议/会话」当成要从零建的东西，实际这部分在本仓库里已是生产件**（`ws-agent.alltman.com:1443`，插件 v0.5.4 已跑通到端）。真正的新增面只有「DSH 执行器接入」这一小块。

---

## 3. 三种落地路线

### 路线 A（最省）：让 Hermes 当守护进程，DSH 退化成一条命令

现有通道已完整：微信/企微 → HarnessMate 网关 → `plugin/hermes/adapter.py`（本机 Hermes）→ Hermes 执行 → 流式回微信。把 DSH 当执行器，只需让 Hermes 在本机调用：

```sh
"/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh" \
  --profile remote headless [--session-id <续接>] "<prompt>"
```

- **删掉**：方案 §3 守护进程、§4 全套协议、§5.2、§6 步骤 1–3 的 launchd 常驻（Hermes 已是常驻服务 `ai.hermes.gateway`）。
- **新增**：约 0 行基础设施 + 1 个技能/工具说明（`sessionId` 映射可放 Hermes 侧存）。
- **代价**：任务会先经 Hermes 的模型（多一跳推理，成本/延迟叠加）；DSH 侧工作区/沙箱策略由 `dsh headless` 自带 `workspace-write` 决定。
- **适用**：目标是「微信里发一句话 → Mac 上跑起来 → 结果回微信」，执行器不必须是 DSH 独占。

### 路线 B（推荐，若执行器必须是 DSH）：DSH 守护进程 + 复用网关与通道协议

保留方案的守护进程，但**总线换成 HarnessMate WS 网关**、**v1.0 协议换成 `hermes_channel_protocol.md`**：

- 守护进程用一个专用 `bot_id`/`bot_key` 连 `wss://ws-agent.alltman.com:1443/ws`（JWT 签 `ws_session_id`），对端 peer 就是微信侧客户端（或平台 UI）；入站收 `data.type=="message"`，出站回 `data.type=="reply"`。
- **删掉**：§4.2–§4.9（自研信封/心跳/超时/会话表一律不要，改用时序见 `hermes_channel_protocol.md` §8）、§4.6 的 relay 实现（约 30 行 + ★reqOwner 全部免掉）、§6 步骤 4。
- **保留并移植**（逻辑，非代码）：§5.2 的按会话串行、全局并发上限、超时 SIGTERM→SIGKILL、ANSI 清洗与批量冲刷；去重与重连退避直接照 `adapter.py` 的参数口径（1→30s、1000 条 LRU）。
- **工作量**：Node 侧约 200–300 行（`common.py:build_session_token` / `build_p2p_envelope` 是同一套 JWT 与信封，照抄语义即可；Python 侧可直接 `import`）。
- **收益**：鉴权、路由、在线状态、UI、文件回传、会话落库、账号白名单全部白得；微信侧只需要一个会说 `{to,data}` 的 peer，不用理解 DSH。

### 路线 C（不建议）：照原方案自建 relay + 自研 v1.0

只有一种情况值得：DSH 远程控制要做成**完全脱离 HarnessMate 的独立开源件**。否则等于长期维护第二套协议（两套心跳、两套会话表、两套文件通道），且路线 B 里已经踩过的坑（去重、取消、输出上限）会在新协议里重踩一遍。

---

### 3.4 已确认 relay = HarnessMate 网关之后，暴露的唯一硬缺口：微信侧 `client` 是谁

网关确认后「总线」不缺了，但方案里那个**「微信客户端（client）」在现有栈里并不存在** —— 今天的微信入口只有两条：Hermes 的企微通道（`wecom:SiLiang`）与手机微信 UI 自动化，二者都终结在 **Hermes 进程**里，不是能说 `{to,data}` 的 peer。所以路线 B 还差最后一段：

| 子路线 | 做法 | 成本 | 代价 |
|---|---|---|---|
| **B1** | 让 Hermes 当中间人（Hermes 已是网关上的 bot）：微信消息 → Hermes → 网关 `{to:<dsh-bot>}` → DSH 执行 → 流式 `reply` 回 Hermes → 回微信 | Hermes 侧加一个「转发给对端 peer 并等 reply」的工具/技能 | 与路线 A 相同的「多一跳模型推理」 |
| B2 | 平台 UI 当客户端：浏览器直接与 `dsh-bot` 对话 | 0 | **不是微信**，丢掉原始需求 |
| B3 | 新写微信→网关 bridge，把微信消息直接投给 `dsh-bot` | 新组件 | 微信渠道实现重写一遍（Hermes 已有） |

**判断**：B1 与路线 A 的差别只在「任务由 DSH 常驻进程执行，还是由 `dsh headless` 一次性执行」。不需要 DSH 常驻会话 → A 更短；需要常驻 → B1 是唯一既保住微信入口、又不重写微信渠道的走法。B2 不满足需求，B3 重复造轮子。**注意**：路线 A 与 B1 都需要微信入口继续走 Hermes，因此「微信里发一句话、DSH 执行、结果回微信」这句话的前提是**微信侧不发语音/不接受 DSH 的交互式审批**（远程审批见方案 §7.2 / §9.9，两条路线同样 fail-closed）。

---

## 4. 代码级复用清单（具体到行）

| 用途 | 位置 |
|---|---|
| JWT（HS256，claim=`ws_session_id`） | `plugin/hermes/common.py:86 build_session_token()` |
| P2P 信封 `{to,data}` | `plugin/hermes/common.py:109 build_p2p_envelope()` |
| 网关地址（统一点对点端点） | `plugin/hermes/adapter.py:62 WS_GATEWAY_WS_URL` |
| 重连退避 / 连接互斥清理 | `plugin/hermes/adapter.py:402 _reconnect_loop()`、`433 _cleanup_ws()` |
| 读循环 / 入站解析 | `plugin/hermes/adapter.py:496 _read_loop()`、`534 _on_gateway_message()` |
| 回包构造与分片 | `plugin/hermes/adapter.py:689 _build_reply_data()`、`732 _send_reply()`、`802 _send_ws()` |
| 文件回传 | `plugin/hermes/file_upload.py::resolve_upload_url()` + `POST /api/open-api/upload-file` |
| 协议白皮书（替代方案 §4） | `plugin/hermes/hermes_channel_protocol.md` |
| 网关规格（替代方案 §4.6） | `gateway/ws_gateway_protocol.md` |

**不可复用**：`adapter.py` 的类本体（`BasePlatformAdapter` 是 Hermes 进程内接口，非 DSH 可用宿主）。

---

## 5. 原方案技术评审（按严重度）

1. **核心路径从未跑通** —— 方案 §8.4 自认「真实 `dsh headless` 调用 ❌未验证」，全部「验证证据」都是 stub dsh 对敲；且 §2.1 卡在 `EPERM: mkdir ~/.dsh/profiles/remote`。**部署前必须先由人工执行 §6 步骤 0**，否则后面全是空跑。
2. **launchd 是否受 DSH 沙箱约束未知**（§2.1 ⚠️ 明说未验证）—— 这决定「常驻守护进程」这一前提成不成立，是整个方案的地基。
3. **DSH 装在独立机器上（2026-10-09 已确认）** —— 文中路径 `/Users/liaosiliang/.dsh/...`、`/Applications/DeepSeek Harness.app` 属于 DSH 那台机器；运行 Hermes 的本机（`/Users/jarvis-liao`）没有 DSH。**后果：路线 A 要跨机就得依赖 SSH 可达，否则只能走 B1**（见 §7）。§1.2 的「已有 WS 网关」已确认为 HarnessMate 网关。
4. **`reqId` 不防重 / `cancel` 软实现 / 离线队列不落盘 / 输出无上限**（§9.1–9.5）—— 前两项在 `adapter.py` 有现成实现可移植；输出建议直接对齐平台口径（4000 字符上限 + 多帧）。
5. **安全**：token 放 body、不入 URL 的取舍正确；但 relay 侧若没有 `userId` 白名单，token 泄露即全权（方案 §7.2 也这么写）—— 平台侧 `allow_from` / `dm_policy` 白名单机制可直接照抄。
6. **提示词注入**（§7.3）在两条路线上风险量级相同（远程无人确认），缓解手段（工作区隔离、凭证不进工作区）建议原样保留。
7. **双协议维护成本**：自研 v1.0 与 `hermes_channel_protocol` 并存，是长期负债。

---

## 6. 建议动作（2026-10-09 更新：网关已确认）

**已确认**：方案 §1.2 的「已有 WebSocket 网关（含微信协议实现）」= **HarnessMate WS 网关** → relay 不需要自建，路线 C 排除。收敛后只剩两个可选，分水岭是「**是否需要 DSH 常驻**」：

1. **路线 A** —— 微信 → Hermes（现有通道）→ `dsh headless` 一次性执行 → 结果回微信：零新基础设施，DSH 的 `sessionId` 由 Hermes 侧存续接。
2. **路线 B1** —— DSH 守护进程作为网关上的**新 peer** 常驻，Hermes 当中间人转发（§3.4）：保留 DSH 自身多轮会话/沙箱，新增约 200–300 行 Node 守护进程 + Hermes 侧一个转发工具；方案 §4.2–§4.9 与 §4.6 整段删除。
3. **共同前置（必须先做）**：人工跑通方案 §6 步骤 0 —— 建 profile（`dsh --from-default-profile web remote`）+ `dsh headless "只回复两个字：pong"` 单跑。该步不通，A / B1 都不必开工。
4. 若走 B1，守护进程源码放本目录（建议 `dsh/agent/`），协议以 `plugin/hermes/hermes_channel_protocol.md` 为唯一来源，不再保留自研 v1.0。

---

## 本目录文件

| 文件 | 说明 |
|---|---|
| `wechat-remote-control-完整方案.md` | 原始方案（原样归档，未改动） |
| `README.md` | 本文件：归档说明 + Hermes 插件复用评估 |
