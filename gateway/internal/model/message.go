// Package model 定义网关内部共享的数据结构与消息常量。
package model

import "encoding/json"

// WSMessage 描述网关点对点转发的统一消息结构。
// 客户端发送时只需提供 to 与 data；网关转发时会补充 from。
type WSMessage struct {
	// To 是目标 ws_session_id，必填。
	To string `json:"to"`
	// From 是发送方 ws_session_id，由网关在转发时写入。
	From string `json:"from,omitempty"`
	// Data 是透传的业务负载。
	Data json.RawMessage `json:"data,omitempty"`
}
