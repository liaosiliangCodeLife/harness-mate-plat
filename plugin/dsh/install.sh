#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# HarnessMate × DSH 插件 — 一键安装脚本
#
# 用法:
#   ./install.sh                  # 交互式输入 bot_id / bot_key
#   ./install.sh <id> <key>       # 直接传入凭据
#
# 可选环境变量:
#   DSH_HOME     默认 ~/.dsh
#   DSH_PROFILE  默认 desktop
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
PROFILE_NAME="${DSH_PROFILE:-desktop}"
PROFILE_DIR="$DSH_HOME/profiles/$PROFILE_NAME"
GATEWAY_URL="wss://ws-agent.alltman.com:1443/ws"

echo "◆ HarnessMate × DSH 插件安装"
echo "  插件目录   : $PLUGIN_DIR"
echo "  DSH profile: $PROFILE_DIR"
echo

# ── 0. 前置检查 ──────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || { echo "✗ 需要 python3（macOS 自带；若缺失请先安装）"; exit 1; }
if [ ! -f "$PLUGIN_DIR/index.js" ] || [ ! -f "$PLUGIN_DIR/package.json" ]; then
  echo "✗ 请在插件目录内运行本脚本（找不到 index.js / package.json）"; exit 1
fi
if [ ! -d "$PROFILE_DIR" ]; then
  echo "✗ 找不到 DSH profile：$PROFILE_DIR"
  echo "  请先安装并启动一次 DSH（DeepSeek Harness）桌面版后重试。"
  echo "  非默认 profile 可用：DSH_PROFILE=名字 ./install.sh"
  exit 1
fi

# ── 1. 读取 bot 凭据（参数 > 交互输入 > 占位符待填）───────────
BOT_ID="${1:-}"
BOT_KEY="${2:-}"
if [ -z "$BOT_ID" ] && [ -t 0 ]; then
  echo "在 HarnessMate 平台「个人空间 → 创建智能体」可拿到 bot_id 和 bot_key。"
  read -r -p "bot_id : " BOT_ID || true
fi
if [ -z "$BOT_KEY" ] && [ -t 0 ]; then
  read -r -p "bot_key: " BOT_KEY || true
fi
BOT_ID="${BOT_ID:-REPLACE_WITH_YOUR_BOT_ID}"
BOT_KEY="${BOT_KEY:-REPLACE_WITH_YOUR_BOT_KEY}"

# ── 2. 备份现有配置 ──────────────────────────────────────────
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$PROFILE_DIR/.harness-mate-backup-$STAMP"
mkdir -p "$BACKUP_DIR"
[ -f "$PROFILE_DIR/package.json" ]     && cp "$PROFILE_DIR/package.json"     "$BACKUP_DIR/"
[ -f "$PROFILE_DIR/cordis.patch.yml" ] && cp "$PROFILE_DIR/cordis.patch.yml" "$BACKUP_DIR/"
echo "→ 已备份到 $BACKUP_DIR"

# ── 3. 注册到 profile（package.json: 依赖 + bundles）─────────
python3 - "$PROFILE_DIR" "$PLUGIN_DIR" <<'PYEOF'
import json, pathlib, sys
profile, plugin = map(pathlib.Path, sys.argv[1:3])
p = profile / "package.json"
data = json.loads(p.read_text())
data.setdefault("dependencies", {})["harness-mate"] = f"link:{plugin}"
bundles = data.setdefault("dsh", {}).setdefault("profile", {}).setdefault("bundles", [])
if "harness-mate" not in bundles:
    bundles.append("harness-mate")
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print("→ package.json 已更新（依赖 + bundles）")
PYEOF

# ── 4. node_modules 链接 ─────────────────────────────────────
mkdir -p "$PROFILE_DIR/node_modules"
ln -sfn "$PLUGIN_DIR" "$PROFILE_DIR/node_modules/harness-mate"
echo "→ node_modules/harness-mate 链接已建立"

# ── 5. 写入网关配置（cordis.patch.yml，幂等）─────────────────
python3 - "$PROFILE_DIR" "$BOT_ID" "$BOT_KEY" "$GATEWAY_URL" "$HOME" <<'PYEOF'
import pathlib, sys
profile = pathlib.Path(sys.argv[1])
bot_id, bot_key, gateway, home = sys.argv[2:6]
p = profile / "cordis.patch.yml"
text = p.read_text() if p.exists() else ""
if "harness-mate" in text:
    print("→ cordis.patch.yml 已包含 harness-mate 配置：保留现有（凭据未改动）")
else:
    block = f"""
# ── HarnessMate 桥（由 install.sh 写入；修改后需重启 DSH 生效）──
- insert:
    - id: harness-mate
      name: 'harness-mate'
      config:
        gatewayUrl: '{gateway}'
        botId: '{bot_id}'
        botKey: '{bot_key}'
        accountId: 'dsh-account'
        dmPolicy: 'open'
        workspace: '{home}'
        # 可选：approvalTimeoutMs: 300000 / typingThrottleMs: 8000 / maxReplyChars: 4000
        # 可选：dmPolicy: 'allowlist' 时用 allowFrom: ['<对端 ws_session_id>'] 限制来源
        # 可选：Agent 工作目录默认为你的主目录；想固定到某个项目目录请改 workspace
"""
    meaningful = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not meaningful or meaningful == ["[]"]:
        text = block.lstrip("\n")            # 空模板（含 "[]" 空数组）→ 整体替换
    else:
        text = text.rstrip("\n") + "\n" + block
    p.write_text(text)
    print("→ cordis.patch.yml 已写入 HarnessMate 配置")
PYEOF

# ── 6. 收尾提示 ──────────────────────────────────────────────
echo
echo "════════════════════════════════════════════════════════════"
if [ "$BOT_ID" = "REPLACE_WITH_YOUR_BOT_ID" ] || [ "$BOT_KEY" = "REPLACE_WITH_YOUR_BOT_KEY" ]; then
  echo "✓ 安装完成（还差凭据）"
  echo
  echo "最后一步：打开文件"
  echo "  $PROFILE_DIR/cordis.patch.yml"
  echo "把 REPLACE_WITH_YOUR_BOT_ID 和 REPLACE_WITH_YOUR_BOT_KEY"
  echo "替换为平台上的真实值。"
else
  echo "✓ 安装完成，凭据已写入（bot_id: ${BOT_ID:0:14}…）"
fi
echo
echo "然后「完全退出并重新打开」DeepSeek Harness（必须重启才生效）。"
echo
echo "验证：重启后给智能体发一条消息，能收到回复即安装成功。"
echo "日志：$HOME/.harness-mate-trace.log"
echo "（出现「WS onopen —— 网关握手成功」即已连上网关）"
echo "════════════════════════════════════════════════════════════"
