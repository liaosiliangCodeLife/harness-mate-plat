---
name: hermes-windows-install
description: "在 Windows 上安装 Hermes Agent（CLI + Electron 桌面端）并排查安装后故障。覆盖：代理端口识别（教程写 7890 实际常见 7897）、受限令牌导致的 schannel TLS 失败、PowerShell 执行策略拦截、桌面端静默秒退（ELECTRON_RUN_AS_NODE 继承）、后台 gateway 未启动导致 Hermes 起不来。"
version: 1.0.0
author: leon-liao
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, windows, install, proxy, electron, china-network, troubleshooting]
prerequisites:
  commands: [powershell, git, curl]
---

# Hermes Agent Windows 安装（含国内网络与踩坑修复）

## 何时使用

- 要在 Windows 上装 Hermes Agent CLI 和/或 Electron 桌面端
- 教程跑完但 `hermes desktop` 打开是白屏 / "Hermes couldn't start"
- 安装脚本访问 GitHub 超时、TLS 报 `SEC_E_NO_CREDENTIALS`
- 桌面端双击闪退、传 `--enable-logging` 报 `bad option:`

## 0. 先侦察（2 分钟，能省 2 小时）

不要直接照抄教程里的端口和"管理员运行"，先问系统要答案：

```powershell
# 1) 真实代理端口：IE/WinINET 设置 + git 配置，比教程可靠
(Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings').ProxyServer
git config --global --get http.proxy
$env:HTTP_PROXY; $env:HTTPS_PROXY

# 2) 端口是否真的在监听（教程的 7890 经常是空的）
foreach ($p in 7890,7891,7897,1080,10808) {
  $t = New-Object Net.Sockets.TcpClient
  try { "$p : $($t.ConnectAsync('127.0.0.1',$p).Wait(800))" } catch { "$p : closed" } finally { $t.Close() }
}

# 3) HTTPS 到底通不通（curl.exe，注意不是 PS 的 curl 别名）
curl.exe -sS -o NUL -w "%{http_code} %{time_total}`n" --max-time 20 --proxy http://127.0.0.1:7897 https://github.com

# 4) 执行策略 / 是否管理员
Get-ExecutionPolicy -List
([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole('Administrator')

# 5) 磁盘与既有安装
"$env:LOCALAPPDATA\hermes exists: $(Test-Path "$env:LOCALAPPDATA\hermes")"
```

判读：

| 现象 | 结论 |
|---|---|
| 端口 7897 开、7890 关 | 用 **7897**，教程的 7890 不适用 |
| 直连 github 超时、走代理 200 | 代理**必须**设，不能省 |
| `Get-ExecutionPolicy -List` 全 Undefined | 生效策略 = **Restricted**，`.ps1` 不能直接跑 |
| `IsInRole('Administrator')` = False | **正常，不用提权**（安装是用户级） |

## 1. 下载脚本并审查（别 `iex (irm ...)` 一把梭）

```powershell
$Work = "$env:TEMP\hermes-setup"; New-Item -ItemType Directory -Force $Work | Out-Null
curl.exe -sSL --proxy http://127.0.0.1:7897 -o "$Work\install.ps1" https://hermes-agent.nousresearch.com/install.ps1
Get-FileHash "$Work\install.ps1" -Algorithm SHA256
```

审查要点（这个官方脚本本身是干净的）：克隆 `github.com/NousResearch/hermes-agent`、装 pinned uv/Python/git 并校验 SHA256、写 `%LOCALAPPDATA%\hermes`、改**用户** PATH、不请求管理员、不碰凭据。

**落地成文件再用 `-File` 跑**，而不是 `iex`：`iex` 无法传参（拿不到 `-NonInteractive`）、失败时 `exit` 会关掉你的窗口、退出码也拿不到。

## 2. 装 CLI（先只装 CLI）

```powershell
$Proxy = 'http://127.0.0.1:7897'
$env:HTTP_PROXY=$Proxy; $env:HTTPS_PROXY=$Proxy; $env:http_proxy=$Proxy; $env:https_proxy=$Proxy
$env:NO_PROXY='localhost,127.0.0.1,npmmirror.com,registry.npmmirror.com'   # 国内镜像直连更快
$env:NPM_CONFIG_REGISTRY='https://registry.npmmirror.com'
$env:ELECTRON_MIRROR='https://npmmirror.com/mirrors/electron/'
$env:ELECTRON_BUILDER_BINARIES_MIRROR='https://npmmirror.com/mirrors/electron-builder-binaries/'

powershell -NoProfile -ExecutionPolicy Bypass -File "$Work\install.ps1" -NonInteractive
```

要点：

- `-ExecutionPolicy Bypass` 是**必需**的：机器策略为 Restricted 时，连 `npm.ps1` 都会报"禁止运行脚本"。脚本内部用 `[ScriptBlock]::Create(...)` 规避，但你手动跑 `.ps1` 不行。
- 镜像用**进程级环境变量**，别 `npm config set` 污染全局；想永久生效再单独设。
- 首次约下载 1.2 GB（ffmpeg 161 MB、Chromium 173 MB、Node 40 MB、Python 48 MB…），代理下 **8–10 分钟**。

装完验证（当前进程 PATH 可能还没刷新，用绝对路径）：

```powershell
& "$env:LOCALAPPDATA\hermes\bin\hermes.exe" --version
cmd /c "where hermes"          # 新终端应能解析；不能就重开终端或查用户 PATH
```

## 3. 装桌面端（单独一步，别和 CLI 合并）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$Work\install.ps1" -Stage desktop
```

**为什么不加 `-IncludeDesktop` 一次装完**：`products` 阶段负责"发布 hermes 命令 + 构建桌面"，桌面构建失败会让整个阶段失败，**CLI 命令就不会发布**——为了桌面端把 CLI 赔进去。分两步，第二次失败也只是没有桌面端。

这一步会：npm install → electron-builder 打包 → 生成 `release\win-unpacked\Hermes.exe` → 给 `ALL APPLICATION PACKAGES` 授 RX（不加这条，Electron 的 GPU/renderer 沙箱会 0x80000003 崩）→ 建桌面/开始菜单快捷方式。

## 4. 启动后台服务（教程漏掉的一步）

`-NonInteractive` 会跳过 `setup` 和 `gateway`。少了 gateway，桌面端能开窗但内容是：

> Hermes couldn't start — background service didn't come up
> `error invoking remote method 'hermes:connection': ... service_manager_unavailable`

```powershell
& "$env:LOCALAPPDATA\hermes\bin\hermes.exe" gateway status   # 常见：任务已注册、进程没起
& "$env:LOCALAPPDATA\hermes\bin\hermes.exe" gateway start
& "$env:LOCALAPPDATA\hermes\bin\hermes.exe" gateway status   # 期望：✓ Gateway process running (PID …)
```

计划任务名 `Hermes_Gateway`；`start` 是 direct spawn，**不要**指望它随当前 shell 退出——用 `status` 复核。

## 5. 验收清单

```powershell
hermes --version                       # v0.22.x + Python 版本 + "Up to date"
hermes desktop --build-only            # ✓ Desktop packaged app ready (…\win-unpacked\Hermes.exe)
hermes gateway status                  # ✓ 进程在跑
Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Hermes.lnk"
Test-Path "$env:USERPROFILE\Desktop\Hermes.lnk"
```

窗口是否真的渲染出来（Electron 常见"进程在但白屏"）：用 `PrintWindow` + `PW_RENDERFULLCONTENT(2)` 截**单个窗口**，别截全屏。截出来是黑的就换全屏截图判断。

## 坑位清单

| # | 坑 | 症状 | 正确做法 |
|---|---|---|---|
| 1 | 端口照抄教程 | 7890 连不上，一切都失败 | 读 WinINET / git config，实际多为 **7897** |
| 2 | `iex (irm ...)` | 无法传参、失败即关窗、无退出码 | 下载成 `.ps1`，`-File` + 参数 |
| 3 | 执行策略 Restricted | `npm.ps1 因为在此系统上禁止运行脚本` | 子进程加 `-ExecutionPolicy Bypass`；node 工具走 `.cmd` |
| 4 | 一步装完 CLI+桌面 | 桌面构建失败 → `hermes` 命令根本不存在 | 先 CLI，再 `-Stage desktop` |
| 5 | `-NonInteractive` 后直接开桌面 | "hermes couldn't start / service_manager_unavailable" | 手动 `hermes gateway start` |
| 6 | 桌面端双击/命令行闪退 | 进程秒退、退出码 0 或 9、无窗口、无日志 | 见下方 `ELECTRON_RUN_AS_NODE` |
| 7 | 教程要求管理员运行 | 多余；非管理员同样装成功 | 用户级安装，UAC 只在 cua-driver 自启时需要 |
| 8 | 受限令牌下下 TLS | `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS`；.NET 报"基础连接已经关闭" | 不是网络问题，是进程令牌读不到 crypto 凭据；换正常权限进程执行 |

## 排错：症状 → 原因 → 修复

### A. `bad option: --enable-logging=stderr` 且秒退

这条报错是 **Node 的**，不是 Chromium 的——说明 `Hermes.exe` 被当成纯 Node 在跑。

**根因**：环境里继承了 `ELECTRON_RUN_AS_NODE=1`。Electron 应用（比如某些 Agent 桌面宿主）会给所有子进程带上它，桌面端一启动就退化成 node，`app` 不存在，静默退出。

```powershell
"ELECTRON_RUN_AS_NODE = '$env:ELECTRON_RUN_AS_NODE'"
Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
Remove-Item Env:NODE_OPTIONS -ErrorAction SilentlyContinue
& "...\win-unpacked\Hermes.exe"
```

从**桌面快捷方式双击**不受影响（Explorer 环境干净）。只有从带该变量的终端/Agent 沙箱里启动才会中招。

### B. 进程在但窗口白 / 立刻退出且无日志

1. 先确认 gateway 在跑（第 4 步）。
2. 用 `Start-Process -RedirectStandardError` 抓 stderr，别指望 GUI 进程的 stdout。
3. 看 `%LOCALAPPDATA%\hermes\logs\{gui,agent,errors}.log`。
4. 事件查看器 `Application` 日志里搜 Hermes；没有记录 + 退出码 0 → 大概率是 A（环境变量）或单实例锁。

### C. CLI 在旧终端里找不到

安装器写的是**用户** PATH。已开着的终端不会刷新：重开终端，或临时
`$env:Path = "$env:LOCALAPPDATA\hermes\bin;$env:Path"`。

### D. cua-driver / computer-use 没生效

安装日志会提示 `Windows cua-driver refresh deferred (autostart registration requires UAC)`。
在**交互式终端**里跑 `hermes computer-use install --upgrade`，会弹 UAC，这是唯一需要提权的地方。

## 完整可复制脚本

```powershell
$Proxy = 'http://127.0.0.1:7897'          # 改成你侦察到的端口
$Work  = "$env:TEMP\hermes-setup"
New-Item -ItemType Directory -Force -Path $Work | Out-Null

$env:HTTP_PROXY=$Proxy; $env:HTTPS_PROXY=$Proxy; $env:http_proxy=$Proxy; $env:https_proxy=$Proxy
$env:NO_PROXY='localhost,127.0.0.1,npmmirror.com,registry.npmmirror.com'
$env:NPM_CONFIG_REGISTRY='https://registry.npmmirror.com'
$env:ELECTRON_MIRROR='https://npmmirror.com/mirrors/electron/'
$env:ELECTRON_BUILDER_BINARIES_MIRROR='https://npmmirror.com/mirrors/electron-builder-binaries/'
Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue

curl.exe -sSL --proxy $Proxy -o "$Work\install.ps1" https://hermes-agent.nousresearch.com/install.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "$Work\install.ps1" -NonInteractive
powershell -NoProfile -ExecutionPolicy Bypass -File "$Work\install.ps1" -Stage desktop

$Hermes = "$env:LOCALAPPDATA\hermes\bin\hermes.exe"
& $Hermes --version
& $Hermes gateway start
& $Hermes gateway status
```

## 参考数据（2026-10，Windows 10 19045 / x64 / 代理 7897）

- 版本：Hermes v0.22.5，commit `bf0203a79`，Python 3.14.9
- 体积：约 **6.1 GB**（`hermes-agent` 3.85 GB + `tools` 1.6 GB）
- 耗时：CLI ≈ 9 min，桌面构建 ≈ 6 min
- 目录：`%LOCALAPPDATA%\hermes\{bin,hermes-agent,tools,skills,logs}`
- 桌面产物：`%LOCALAPPDATA%\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`

## 装成 Hermes 技能（可选）

本文件是标准 SKILL.md 格式，但技能需要放在**同名目录**里才会被扫描：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\Desktop\hermes-windows-install" | Out-Null
Move-Item "$env:USERPROFILE\Desktop\SKILL.md" "$env:USERPROFILE\Desktop\hermes-windows-install\SKILL.md"
hermes skills install "$env:USERPROFILE\Desktop\hermes-windows-install"
```
