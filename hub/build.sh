#!/usr/bin/env bash
# This is the projet for brtc R&D Platform
# @Author Leon-liao <liaosiliang@alltman.com>
# @Description //构建 Hub 二进制
# @File: build.sh
# @Time: 2026/10/23 10:39:00
# @All Rights Reserve By Brtc

# 构建当前平台与 linux/amd64 产物到 build/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v go >/dev/null 2>&1; then
  echo "未找到 Go 工具链，请安装 Go 1.25+ 并加入 PATH" >&2
  exit 1
fi

LDFLAGS="-s -w"
mkdir -p build/linux

echo "构建当前平台..."
CGO_ENABLED=0 go build -ldflags "$LDFLAGS" -o build/hub .
echo "当前平台构建完成: build/hub"

echo "构建 linux/amd64..."
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags "$LDFLAGS" -o build/linux/hub .
echo "Linux 构建完成: build/linux/hub"
