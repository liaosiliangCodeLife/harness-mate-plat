package model

import "github.com/golang-jwt/jwt/v5"

// SessionClaims 表示 WebSocket 握手阶段提交的 JWT Claims。
// 网关仅识别 ws_session_id，不做 account/device/hermes 等业务区分。
type SessionClaims struct {
	// WSSessionID 是连接唯一标识，用于点对点路由。
	WSSessionID string `json:"ws_session_id"`
	// RegisteredClaims 是 JWT 标准注册字段。
	jwt.RegisteredClaims
}
