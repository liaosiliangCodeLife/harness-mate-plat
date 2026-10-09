# HarnessMate 插件安装指南

> **读者**：负责把 HarnessMate 平台接进**本机 Hermes Agent** 的 AI Agent（或运维同学）。
> **做完的效果**：浏览器上跟智能体对话 → 消息经平台 WS 网关 → 落到你本机的 Hermes Agent 执行 → 回复原路返回；图片与文件双向传。
> 文中所有 `<...>` 都要换成你的实际值；命令可直接复制执行。

---

## 0. 极简版（三条命令，已实测）

```bash
# 1) 安装（自动装依赖并启用；插件在仓库的 plugin/ 子目录里）
hermes plugins install liaosiliangCodeLife/harness-mate-plat/plugin/hermes --yes-deps --enable

# 2) 填身份：把 <...> 换成平台侧给你的值
cat >> ~/.hermes/.env <<'EOF'
HARNESS_MATE_BOT_ID=<bot_id>
HARNESS_MATE_BOT_KEY=<bot_key>
EOF

# 3) 让插件连你自己的网关（默认指向作者的示例网关，见 4.1）
#    编辑 ~/.hermes/plugins/HarnessMate/adapter.py 第 62 行：WS_GATEWAY_WS_URL

hermes gateway restart        # 重启后插件才会连上网关
```

---

## 1. 前置条件

| 前置 | 怎么确认 |
|---|---|
| 本机已装 Hermes Agent | `hermes --version` |
| 平台侧已部署（api + WS 网关 + ui） | 浏览器能打开平台并登录 |
| 已创建智能体，拿到 `bot_id` 与 `bot_key` | 平台 →「个人空间」→ 创建智能体（填网关地址与密钥） |
| 网关 WebSocket 地址 | 形如 `wss://<网关域名>:<端口>/ws` |
| 网络可达 | `nc -vz <网关域名> <端口>` 能通 |

---

## 2. 安装插件

### 方式 A（推荐）：一条命令

```bash
hermes plugins install liaosiliangCodeLife/harness-mate-plat/plugin/hermes --yes-deps --enable
```

- 插件在仓库的 `plugin/` 子目录，Hermes 支持 `owner/repo/子目录` 写法（也接受 `https://github.com/owner/repo.git/plugin` 或 `owner/repo#plugin`）。
- `--yes-deps`：非交互地同意安装 Python 依赖。**不加它，安装会停在「依赖确认」这一步**（SSH/CI 场景尤其要加）。
- `--enable`：装完直接启用；不加则事后 `hermes plugins enable HarnessMate`。
- 落点：`~/.hermes/plugins/HarnessMate/`。

装完可用 `hermes plugins list` 确认。

### 方式 B：手动拷贝（离线 / 想自己管目录）

```bash
git clone https://github.com/liaosiliangCodeLife/harness-mate-plat.git
mkdir -p ~/.hermes/plugins
cp -R harness-mate-plat/plugin ~/.hermes/plugins/HarnessMate
hermes plugins adopt ~/.hermes/plugins/HarnessMate    # 可选：纳入安装来源跟踪
hermes plugins enable HarnessMate
```

---

## 3. Python 依赖

插件依赖 `websockets>=12,<15` 与 `PyJWT>=2,<3`，必须装进 **Hermes 自己的 Python 环境**（不是系统 `python3`）：

```bash
~/.hermes/tools/python-*/bin/python3 -m pip install -r ~/.hermes/plugins/HarnessMate/requirements.txt
~/.hermes/tools/python-*/bin/python3 -c "import websockets, jwt; print('deps ok')"   # 自检
```

> 走方式 A 且带 `--yes-deps` 时 Hermes 已经代装，直接跑自检那行即可。
> 解释器目录名随 Hermes 版本变化，用通配符；若本机是 venv 形态的 Hermes，则用该 venv 的 `python`。

---

## 4. 配置

优先级：**插件 `plugin.yaml` 的 `config` 段 > 环境变量**（`adapter.py` 先读 config，取不到再用环境变量）。

### 4.1 网关地址（必须确认）

插件默认连的是作者部署的示例网关，自部署**必须改**：

```python
# ~/.hermes/plugins/HarnessMate/adapter.py  第 62 行
WS_GATEWAY_WS_URL = "wss://ws-agent.alltman.com:1443/ws"
```

改成你的网关地址，格式 `wss://<域名或IP>:<端口>/ws`；插件连接时会自动追加 `?token=<JWT>`。
（该地址目前是硬编码，没有环境变量可覆盖。）

### 4.2 bot_id / bot_key（必填）

- `bot_id`：该智能体在网关上的身份（即 `ws_session_id`）
- `bot_key`：给 WS 连接 JWT 做 HMAC 签名用的密钥

两个值在平台「个人空间 → 创建智能体」时就是填的这两个。二选一写入：

**写法 1：写进 Hermes 的环境文件（推荐）**

```bash
cat >> ~/.hermes/.env <<'EOF'
HARNESS_MATE_BOT_ID=<bot_id>
HARNESS_MATE_BOT_KEY=<bot_key>
EOF
```

**写法 2：编辑插件目录的 `plugin.yaml`**

```yaml
config:
  bot_id: "<bot_id>"
  bot_key: "<bot_key>"
```

> ⚠️ `bot_key` 必须与网关侧的 `JWT_SECRET` 一致，否则连得上也会被网关拒绝。

### 4.3 可选配置

| plugin.yaml `config` | 环境变量 | 默认 | 作用 |
|---|---|---|---|
| `upload_url` | `HARNESS_MATE_UPLOAD_URL` | `https://harness.alltman.com/api/open-api/upload-file` | Agent 回传本机文件时上传到的平台接口；自部署改成自己的域名 |
| `dm_policy` | `HARNESS_MATE_DM_POLICY` | `open` | 谁能给它发消息：`open` / `allowlist` / `disabled` |
| `allow_from` | `HARNESS_MATE_ALLOWED_PEERS`（旧名 `HARNESS_MATE_ALLOWED_DEVICES`） | 空 | 白名单 peer 的 `ws_session_id`，支持 `*` 通配 |
| — | `HARNESS_MATE_ALLOW_ALL_DEVICES` | 空 | 调试用：放行全部 peer |
| — | `HARNESS_MATE_PING_INTERVAL` / `HARNESS_MATE_PING_TIMEOUT` | 50 / 90 | WS 心跳间隔与超时（秒） |
| — | `HARNESS_MATE_RECONNECT_MIN_DELAY` / `_MAX_DELAY` | 1 / 30 | 断线重连退避（秒） |
| — | `HARNESS_MATE_TYPING_INTERVAL` | 8 | 「正在输入」节流（秒） |

---

## 5. 生效

平台插件跑在 Hermes 进程里，装完或改完配置都要让它重新加载：

```bash
hermes gateway restart     # 或直接退出桌面端重新打开
hermes gateway status      # 确认在跑
```

---

## 6. 验证（按顺序，全过才算装好）

**① 插件已启用**

```bash
hermes plugins list | grep -i harnessmate     # 期望 Status: enabled
hermes plugins show HarnessMate               # 期望 required env 不再是「未配置」
```

**② 插件能被 Hermes 正常加载**（对目录跑同样可以，适合装前自检）

```bash
hermes plugins doctor /path/to/harness-mate-plat/plugin
# 期望输出：OK: runtime discovery, manifest parsing, import, and registration passed
```

**③ 日志里出现连接成功**（关键判据）

```
harness_mate 已连接 WS 网关: bot_id=<你的 bot_id>
```

断线会打印 `harness_mate Gateway 断线，N 秒后重连 (bot_id=...)`，恢复后打印 `harness_mate 已重连 WS 网关`。

**④ 端到端**：浏览器打开平台 → 进入智能体 → 新建会话 → 发「你好」，本机 Agent 应在几秒内回复。

**⑤ 文件回传**：让 Agent 发一张本机图片，聊天里应出现缩略图（走 `upload_url` 链路）。

---

## 7. 排障

| 症状 | 原因 / 处理 |
|---|---|
| 日志：`harness_mate 缺少 bot_id 或 bot_key` | 配置没读到：核对 `~/.hermes/.env` 或 `plugin.yaml` 的 `config`，改完要重启 |
| 连上就被断开 / 被网关拒绝 | `bot_key` 与网关 `JWT_SECRET` 不一致 |
| 一直「断线，N 秒后重连」 | 网关地址或端口不通：确认 `WS_GATEWAY_WS_URL`，`nc -vz <host> <port>` 测通；同一 `ws_session_id` 只允许一条连接，别多开 |
| 平台发消息没反应、日志也没有入站 | `dm_policy=allowlist` 但对方 peer 不在 `allow_from` 里 |
| 图片/文件回传失败 | `upload_url` 不对，或平台侧 `POST /api/open-api/upload-file` 不可达／被限流 |
| `hermes plugins list` 里是 disabled | `hermes plugins enable HarnessMate` |
| 装完没连上、日志里没有任何 harness 输出 | 忘了重启：`hermes gateway restart` |

排障小工具：本目录的 `app_chat.py` 是不经过 Hermes、直连网关的测试客户端，可用来单独验证网关侧是否正常（`python app_chat.py --help` 看参数）。

---

## 8. 卸载

```bash
hermes plugins remove HarnessMate
```

残留（可选清理）：`~/.hermes/.env` 里的 `HARNESS_MATE_*` 行、`~/.hermes/config.yaml` 的 `plugins` 段。

---

## 9. 本目录文件说明

| 文件 | 作用 |
|---|---|
| `plugin.yaml` | 插件清单：名称、kind、版本、需要/可选配置项 |
| `adapter.py` | 主逻辑：连网关、收发消息、流式与中断；**第 62 行是网关地址** |
| `common.py` | JWT 构造、P2P 信封、回复字段提取等工具 |
| `file_upload.py` | Agent 回传本机文件的上传实现（`resolve_upload_url`） |
| `hermes_channel_protocol.md` | 平台与 Agent 之间的通道协议（换别的 Agent 也照它实现） |
| `app_chat.py` | 直连网关的测试客户端（排障用） |
| `AGENTS.md` | 适配器开发约束（改插件前先读） |
