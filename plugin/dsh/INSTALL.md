# HarnessMate × DSH 插件 —— 安装指南

把 **DSH（DeepSeek Harness）** 接入 **HarnessMate 平台**：让你电脑上的本机 AI Agent 变成手机 / 浏览器随取随用的助手（消息、文件、问答全打通）。

支持 **macOS 与 Windows**，安装只需要 3 步：**放置 → 运行安装脚本 → 重启 DSH**。

平台项目：<https://github.com/liaosiliangCodeLife/harness-mate-plat>

---

## 前置条件

1. 已安装 **DeepSeek Harness 桌面版**（v0.2.0-rc.2 及以上），并且**至少启动过一次**；
2. 已在 **HarnessMate 平台**创建好智能体，拿到 **`bot_id`** 和 **`bot_key`**：
   - 打开平台网页（示例：`https://harness.alltman.com`）→ 登录 → 「个人空间」→「创建智能体」
   - 创建完成后复制该智能体的 `bot_id` 与 `bot_key`（密钥只显示一次，请妥善保存）

## 安装（3 步）

### 第 1 步：安置插件目录

把本文件夹（`harness-mate`）放到一个固定的位置，例如：

- macOS：`~/Documents/harness-mate`
- Windows：`C:\Users\你的用户名\Documents\harness-mate`

> ⚠️ 之后不要随意移动它（移动后在新位置重新运行一次安装脚本即可）。

### 第 2 步：运行安装脚本

**macOS** —— 打开「终端」（Terminal.app）：

```bash
cd ~/Documents/harness-mate
./install.sh
```

**Windows** —— 在插件文件夹中打开 PowerShell（文件夹空白处按住 Shift + 右键 →「在此处打开 PowerShell 窗口」），执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

> Windows 上本地脚本默认被禁止运行，必须带 `-ExecutionPolicy Bypass`，否则会提示"因为在此系统上禁止运行脚本"。

脚本会提示你输入 `bot_id` 和 `bot_key`，然后自动完成全部配置。也可以一步传入：

```bash
# macOS
./install.sh <你的 bot_id> <你的 bot_key>
```

```powershell
# Windows
.\install.ps1 -BotId <你的 bot_id> -BotKey <你的 bot_key>
```

> macOS 若提示没有执行权限，先运行 `chmod +x install.sh` 再执行。

### 第 3 步：重启 DSH

**完全退出** DeepSeek Harness（macOS：菜单栏 → 退出；Windows：托盘图标 → 退出，而不是只关窗口），再重新打开。

---

## 验证安装成功

在平台网页 / 手机 App 上给这个智能体发一条消息（比如「你好」）：

- ✅ **能收到回复 = 安装成功**，此后你的本机 Agent 就在平台上随叫随到；
- 📄 排查用日志：
  - macOS：`~/.harness-mate-trace.log`
  - Windows：`C:\Users\你的用户名\.harness-mate-trace.log`
  - 出现 `WS onopen —— 网关握手成功` → 插件已连上网关
  - 出现 `缺少配置：gatewayUrl / botId / botKey` → 凭据没填对
  - 文件不在 / 不更新 → 插件没被加载，见下方 FAQ

## 常见问题（FAQ）

**Q：发消息没反应？**
依次检查：
1. DSH 是否「完全退出」后重新打开过（改配置后必须重启才生效）；
2. 配置文件里的 `botId` / `botKey` 是否已替换成真实值（不能残留 `REPLACE_WITH_...`）：
   - macOS：`~/.dsh/profiles/desktop/cordis.patch.yml`
   - Windows：`C:\Users\你的用户名\.dsh\profiles\desktop\cordis.patch.yml`
3. 看日志文件的最后几行，按提示定位。

**Q：Windows 提示"禁止运行脚本"？**
用完整命令运行：`powershell -ExecutionPolicy Bypass -File .\install.ps1`（或在系统设置里放开脚本执行策略）。

**Q：Windows 上创建链接失败？**
安装脚本使用目录 junction，普通用户即可创建；若仍失败，以管理员身份重跑一次安装脚本。

**Q：它看不到我电脑上的文件？**
Agent 的默认工作目录是你的用户主目录（`~` / `C:\Users\你的用户名`），一般可以直接访问其中内容。想固定到某个项目目录，把 `cordis.patch.yml` 里的 `workspace` 改成该目录后重启 DSH。

**Q：怎么重新安装 / 换位置？**
把插件目录移动到新位置后，在新位置重新运行安装脚本即可（脚本幂等；已填写的凭据不会被覆盖）。

**Q：怎么卸载？**
1. 编辑 profile 的 `package.json`：从 `dependencies` 和 `dsh.profile.bundles` 中删除 `harness-mate` 相关行；
2. 删除链接：

   ```bash
   # macOS
   rm ~/.dsh/profiles/desktop/node_modules/harness-mate
   ```

   ```powershell
   # Windows
   cmd /c rmdir "%USERPROFILE%\.dsh\profiles\desktop\node_modules\harness-mate"
   ```

3. 编辑 `cordis.patch.yml`：删除 `id: harness-mate` 的那个 `- insert:` 块；
4. 重启 DSH。

> 安装脚本每次运行都会把改前的配置备份到 profile 目录下 `.harness-mate-backup-<时间戳>` 文件夹，需要回滚时从这里恢复。

## 手动安装（不使用脚本时）

1. **注册插件** — 编辑 profile 的 `package.json`
   （macOS：`~/.dsh/profiles/desktop/package.json`；Windows：`%USERPROFILE%\.dsh\profiles\desktop\package.json`）：

   ```json
   {
     "dependencies": {
       "harness-mate": "link:插件的绝对路径"
     },
     "dsh": {
       "profile": {
         "bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app", "harness-mate"]
       }
     }
   }
   ```

2. **建立链接**（替换为插件的绝对路径）：

   ```bash
   # macOS
   ln -sfn /绝对路径/harness-mate ~/.dsh/profiles/desktop/node_modules/harness-mate
   ```

   ```powershell
   # Windows（junction，无需管理员）
   cmd /c mklink /J "%USERPROFILE%\.dsh\profiles\desktop\node_modules\harness-mate" "C:\绝对路径\harness-mate"
   ```

3. **写入配置** — 在 `cordis.patch.yml` 末尾添加：

   ```yaml
   - insert:
       - id: harness-mate
         name: 'harness-mate'
         config:
           gatewayUrl: 'wss://ws-agent.alltman.com:1443/ws'
           botId: '你的 bot_id'
           botKey: '你的 bot_key'
           accountId: 'dsh-account'
           dmPolicy: 'open'
           workspace: '你的主目录绝对路径'
   ```

4. **重启 DSH**。

## 可选配置项

在 `cordis.patch.yml` 的 `config` 下按需添加（改完重启 DSH）：

| 字段 | 默认 | 说明 |
|---|---|---|
| `workspace` | 你的主目录 | Agent 工作目录（读写文件的根） |
| `dmPolicy` | `open` | `open` 谁都能发消息；`allowlist` 仅白名单（配合 `allowFrom: ['对端 ws_session_id']`）；`disabled` 停用 |
| `approvalTimeoutMs` | `300000` | 高危操作审批超时（毫秒），超时按拒绝处理 |
| `typingThrottleMs` | `8000` | 「思考中」状态节流 |
| `maxReplyChars` | `4000` | 单条回复最大字符数 |
| `forwardReasoning` | `false` | 是否把思考过程也发到聊天里 |
| `traceFile` | `<workspace>/.harness-mate-trace.log` | 插件日志文件位置 |

## 文件一览（本插件包）

```
harness-mate/
├── index.js            # 插件主程序（DSH cordis 插件）
├── package.json        # 插件清单（bundle 契约 + 图标声明）
├── cordis.patch.yml    # 插件默认配置（安装时由脚本/你写入真实凭据）
├── icon.svg            # 插件图标（DSH 插件页显示）
├── locale/             # 中英双语标题与描述
│   ├── en.json
│   └── zh.json
├── install.sh          # macOS 一键安装脚本
├── install.ps1         # Windows 一键安装脚本（PowerShell）
└── INSTALL.md          # 本文档
```
