#!/usr/bin/env bash
# 构建 Windows / Linux 产物到 build/{platform}/{platform}-{version}-{timestamp}/
# 命名规则: platform-version-时间戳(到分钟)，例如 linux-v0.0.3-202607021430
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v go >/dev/null 2>&1; then
  echo "未找到 Go 工具链，请安装 Go 1.22+ 并加入 PATH" >&2
  exit 1
fi

VERSION_FILE="$SCRIPT_DIR/VERSION"
if [[ ! -f "$VERSION_FILE" ]]; then
  echo "未找到 VERSION 文件: $VERSION_FILE" >&2
  exit 1
fi

VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
if [[ -z "$VERSION" ]]; then
  echo "VERSION 文件内容为空" >&2
  exit 1
fi

TIMESTAMP="$(date +%Y%m%d%H%M)"
LDFLAGS="-s -w"

new_package_dir() {
  local platform="$1"
  local package_name="${platform}-${VERSION}-${TIMESTAMP}"
  local package_dir="$SCRIPT_DIR/build/${platform}/${package_name}"
  mkdir -p "$package_dir"
  printf '%s' "$package_dir"
}

copy_runtime_files() {
  local target_dir="$1"
  local platform="$2"
  cp "$SCRIPT_DIR/.env.example" "$target_dir/.env.example"
  cp "$SCRIPT_DIR/VERSION" "$target_dir/VERSION"
  if [[ "$platform" == "windows" ]]; then
    cp "$SCRIPT_DIR/build/windows/run.ps1" "$target_dir/run.ps1"
    cp "$SCRIPT_DIR/build/windows/run.bat" "$target_dir/run.bat"
  else
    cp "$SCRIPT_DIR/build/linux/run.sh" "$target_dir/run.sh"
    chmod +x "$target_dir/run.sh"
  fi
}

WINDOWS_DIR="$(new_package_dir windows)"
GOOS=windows GOARCH=amd64 go build -ldflags "$LDFLAGS" -o "$WINDOWS_DIR/ws_gateway.exe" .
copy_runtime_files "$WINDOWS_DIR" windows
echo "Windows 构建完成: $WINDOWS_DIR"

LINUX_DIR="$(new_package_dir linux)"
GOOS=linux GOARCH=amd64 go build -ldflags "$LDFLAGS" -o "$LINUX_DIR/ws_gateway" .
copy_runtime_files "$LINUX_DIR" linux
chmod +x "$LINUX_DIR/ws_gateway"
echo "Linux 构建完成: $LINUX_DIR"

echo
echo "版本: $VERSION"
echo "时间戳: $TIMESTAMP"
echo "产物目录:"
echo "  build/windows/windows-${VERSION}-${TIMESTAMP}"
echo "  build/linux/linux-${VERSION}-${TIMESTAMP}"
