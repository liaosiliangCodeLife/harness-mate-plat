/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //网关帧结构，自 gateway/internal/model/message.go 复制
 * @File: message.go
 * @Time: 2026/10/23 10:39:00
 * @All Rights Reserve By Brtc
 */

// Package model 定义 Hub 与网关之间转发使用的帧结构。
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
