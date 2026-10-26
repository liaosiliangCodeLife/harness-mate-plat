// This is the projet for brtc R&D Platform
// @Author Leon-liao <liaosiliang@alltman.com>
// @Description //Hub Go module，依赖版本与 gateway/go.mod 对齐
// @File: go.mod
// @Time: 2026/10/23 10:39:00
// @All Rights Reserve By Brtc

module hub

go 1.25.0

require (
	github.com/gorilla/websocket v1.5.3
	github.com/redis/go-redis/v9 v9.21.0
)
