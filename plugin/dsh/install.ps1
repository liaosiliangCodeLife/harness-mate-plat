# ═══════════════════════════════════════════════════════════════
# HarnessMate × DSH 插件 — Windows 安装脚本（PowerShell）
#
# 用法（在插件目录内打开 PowerShell 执行）:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -BotId <id> -BotKey <key>
#
# 可选环境变量:
#   DSH_HOME     默认 %USERPROFILE%\.dsh
#   DSH_PROFILE  默认 desktop
# ═══════════════════════════════════════════════════════════════
param(
  [string]$BotId = "",
  [string]$BotKey = ""
)
$ErrorActionPreference = "Stop"

$PluginDir   = $PSScriptRoot
$DshHome     = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE ".dsh" }
$ProfileName = if ($env:DSH_PROFILE) { $env:DSH_PROFILE } else { "desktop" }
$ProfileDir  = Join-Path $DshHome (Join-Path "profiles" $ProfileName)
$GatewayUrl  = "wss://ws-agent.alltman.com:1443/ws"
$HomeDir     = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }
$utf8NoBom   = New-Object System.Text.UTF8Encoding($false)

Write-Host "◆ HarnessMate × DSH 插件安装"
Write-Host "  插件目录   : $PluginDir"
Write-Host "  DSH profile: $ProfileDir"
Write-Host ""

# ── 0. 前置检查 ──────────────────────────────────────────────
if (-not (Test-Path (Join-Path $PluginDir "index.js")) -or -not (Test-Path (Join-Path $PluginDir "package.json"))) {
  Write-Host "✗ 请在插件目录内运行本脚本（找不到 index.js / package.json）" -ForegroundColor Red
  exit 1
}
if (-not (Test-Path $ProfileDir)) {
  Write-Host "✗ 找不到 DSH profile：$ProfileDir" -ForegroundColor Red
  Write-Host "  请先安装并启动一次 DSH（DeepSeek Harness）后重试。"
  Write-Host "  非默认 profile 可用：设置环境变量 DSH_PROFILE 后重试"
  exit 1
}

# ── 1. 读取 bot 凭据（参数 > 交互输入 > 占位符待填）───────────
if (-not $BotId -and [Environment]::UserInteractive) { $BotId  = Read-Host "bot_id （平台 → 个人空间 → 创建智能体）" }
if (-not $BotKey -and [Environment]::UserInteractive) { $BotKey = Read-Host "bot_key" }
if (-not $BotId)  { $BotId  = "REPLACE_WITH_YOUR_BOT_ID" }
if (-not $BotKey) { $BotKey = "REPLACE_WITH_YOUR_BOT_KEY" }

# ── 2. 备份现有配置 ──────────────────────────────────────────
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $ProfileDir ".harness-mate-backup-$stamp"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
foreach ($f in @("package.json", "cordis.patch.yml")) {
  $src = Join-Path $ProfileDir $f
  if (Test-Path $src) { Copy-Item $src $backupDir }
}
Write-Host "→ 已备份到 $backupDir"

# ── 3. 注册到 profile（package.json：依赖 + bundles）─────────
$pkgPath = Join-Path $ProfileDir "package.json"
$pkg = Get-Content -Raw -Encoding UTF8 $pkgPath | ConvertFrom-Json
if (-not $pkg.dependencies) { $pkg | Add-Member -NotePropertyName dependencies -NotePropertyValue ([pscustomobject]@{}) -Force }
$pkg.dependencies | Add-Member -NotePropertyName "harness-mate" -NotePropertyValue ("link:" + $PluginDir) -Force
if (-not $pkg.dsh) { $pkg | Add-Member -NotePropertyName dsh -NotePropertyValue ([pscustomobject]@{}) -Force }
if (-not $pkg.dsh.profile) { $pkg.dsh | Add-Member -NotePropertyName profile -NotePropertyValue ([pscustomobject]@{}) -Force }
$bundles = $pkg.dsh.profile.bundles
if ($bundles -is [string]) { $bundles = @($bundles) }   # PS 5.1 会把单元素数组解析成字符串
if (-not $bundles) { $bundles = @() }
if ($bundles -notcontains "harness-mate") { $bundles = @($bundles) + "harness-mate" }
$pkg.dsh.profile | Add-Member -NotePropertyName bundles -NotePropertyValue $bundles -Force
[System.IO.File]::WriteAllText($pkgPath, ($pkg | ConvertTo-Json -Depth 100) + "`n", $utf8NoBom)

# 写回验证（JSON 语义正确性 + 目标字段齐全）
$check = Get-Content -Raw -Encoding UTF8 $pkgPath | ConvertFrom-Json
$okDep = $check.dependencies.'harness-mate' -like "link:*"
$okBundle = @($check.dsh.profile.bundles) -contains "harness-mate"
if (-not ($okDep -and $okBundle)) {
  Write-Host "✗ package.json 写入验证失败，请从备份恢复：$backupDir" -ForegroundColor Red
  exit 1
}
Write-Host "→ package.json 已更新（依赖 + bundles）"

# ── 4. node_modules 链接（junction，普通用户即可）────────────
$nmDir = Join-Path $ProfileDir "node_modules"
New-Item -ItemType Directory -Force -Path $nmDir | Out-Null
$linkPath = Join-Path $nmDir "harness-mate"
if ($env:OS -eq "Windows_NT") {
  & cmd.exe /c "rmdir `"$linkPath`"" 2>$null                              # 只删链接本身（不碰目标目录），不存在则忽略
  & cmd.exe /c "mklink /J `"$linkPath`" `"$PluginDir`"" | Out-Null        # junction：普通用户即可创建
} else {
  # 非 Windows 的 PowerShell（开发/测试环境）：用符号链接
  if (Test-Path $linkPath) { Remove-Item $linkPath -Force }
  New-Item -ItemType SymbolicLink -Path $linkPath -Target $PluginDir | Out-Null
}
if (-not (Test-Path (Join-Path $linkPath "index.js"))) {
  Write-Host "✗ node_modules 链接创建失败，请检查目录权限" -ForegroundColor Red
  exit 1
}
Write-Host "→ node_modules\harness-mate 链接已建立"

# ── 5. 写入网关配置（cordis.patch.yml，幂等）─────────────────
$patchPath = Join-Path $ProfileDir "cordis.patch.yml"
$text = if (Test-Path $patchPath) { [System.IO.File]::ReadAllText($patchPath) } else { "" }
if ($text -match "harness-mate") {
  Write-Host "→ cordis.patch.yml 已包含 harness-mate 配置：保留现有（凭据未改动）"
} else {
  $block = @"
# ── HarnessMate 桥（由 install.ps1 写入；修改后需重启 DSH 生效）──
- insert:
    - id: harness-mate
      name: 'harness-mate'
      config:
        gatewayUrl: '$GatewayUrl'
        botId: '$BotId'
        botKey: '$BotKey'
        accountId: 'dsh-account'
        dmPolicy: 'open'
        workspace: '$HomeDir'
        # 可选：approvalTimeoutMs: 300000 / typingThrottleMs: 8000 / maxReplyChars: 4000
        # 可选：dmPolicy: 'allowlist' 时用 allowFrom: ['<对端 ws_session_id>'] 限制来源
        # 可选：Agent 工作目录默认是你的用户目录；想固定到某个项目目录请改 workspace
"@
  $meaningful = @(($text -split "`n") | Where-Object { $t = $_.Trim(); $t -ne "" -and -not $t.StartsWith("#") })
  if ($meaningful.Count -eq 0 -or ($meaningful.Count -eq 1 -and $meaningful[0].Trim() -eq "[]")) {
    $out = $block + "`n"                                        # 空模板（含 "[]" 空数组）→ 整体替换
  } else {
    $out = $text.TrimEnd("`r", "`n") + "`r`n`r`n" + $block + "`n"   # 已有内容 → 追加
  }
  [System.IO.File]::WriteAllText($patchPath, $out, $utf8NoBom)
  Write-Host "→ cordis.patch.yml 已写入 HarnessMate 配置"
}

# ── 6. 收尾提示 ──────────────────────────────────────────────
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════"
if ($BotId -eq "REPLACE_WITH_YOUR_BOT_ID" -or $BotKey -eq "REPLACE_WITH_YOUR_BOT_KEY") {
  Write-Host "✓ 安装完成（还差凭据）"
  Write-Host ""
  Write-Host "最后一步：打开文件"
  Write-Host "  $patchPath"
  Write-Host "把 REPLACE_WITH_YOUR_BOT_ID 和 REPLACE_WITH_YOUR_BOT_KEY 替换为真实值。"
} else {
  $shown = $BotId.Substring(0, [Math]::Min(14, $BotId.Length))
  Write-Host "✓ 安装完成，凭据已写入（bot_id: $shown…）"
}
Write-Host ""
Write-Host "然后「完全退出并重新打开」DeepSeek Harness（必须重启才生效）。"
Write-Host ""
Write-Host "验证：重启后给智能体发一条消息，能收到回复即安装成功。"
Write-Host "日志：$HomeDir\.harness-mate-trace.log"
Write-Host "（出现「WS onopen —— 网关握手成功」即已连上网关）"
Write-Host "════════════════════════════════════════════════════════════"
