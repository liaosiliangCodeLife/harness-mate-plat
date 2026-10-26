/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //Hub 连接网关使用的 HS256 JWT 签发
 * @File: jwt.go
 * @Time: 2026/10/23 10:39:00
 * @All Rights Reserve By Brtc
 */

// Package jwt 使用标准库签发 WebSocket 连接 JWT。
// 算法与网关验签一致：HMAC-SHA256，密钥为调用方传入的 gateway_key。
package jwt

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

const tokenTTL = 30 * 24 * time.Hour

// Claims 是连接令牌的全部声明，不含业务字段。
type Claims struct {
	// WSSessionID 是连接身份，Hub 优先使用 agent.peer_id，为空时回退 hub-<bot_id>。
	WSSessionID string `json:"ws_session_id"`
	// Iat 是签发时间，Unix 秒。
	Iat int64 `json:"iat"`
	// Exp 是过期时间，Unix 秒。
	Exp int64 `json:"exp"`
}

type header struct {
	Alg string `json:"alg"`
	Typ string `json:"typ"`
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: Sign(secret, wsSessionID string)
 * @Description //用 HS256 签发只含 ws_session_id、iat、exp 的连接令牌，有效期 30 天。Hub 优先使用 agent.peer_id，为空时回退 hub-<bot_id>
 * @Date :2026/10/23 10:39:00
 * @Param: secret HMAC 密钥，即 gateway_key；wsSessionID 连接身份，Hub 优先使用 agent.peer_id，为空时回退 hub-<bot_id>
 * @return: JWT 字符串；参数为空或编码失败时返回 error
 */
func Sign(secret, wsSessionID string) (string, error) {
	if strings.TrimSpace(secret) == "" {
		return "", fmt.Errorf("jwt secret is required")
	}
	if strings.TrimSpace(wsSessionID) == "" {
		return "", fmt.Errorf("ws_session_id is required")
	}

	now := time.Now()
	headerJSON, err := json.Marshal(header{Alg: "HS256", Typ: "JWT"})
	if err != nil {
		return "", fmt.Errorf("marshal jwt header: %w", err)
	}
	payloadJSON, err := json.Marshal(Claims{
		WSSessionID: wsSessionID,
		Iat:         now.Unix(),
		Exp:         now.Add(tokenTTL).Unix(),
	})
	if err != nil {
		return "", fmt.Errorf("marshal jwt claims: %w", err)
	}

	unsigned := encodeSegment(headerJSON) + "." + encodeSegment(payloadJSON)
	mac := hmac.New(sha256.New, []byte(secret))
	if _, err := mac.Write([]byte(unsigned)); err != nil {
		return "", fmt.Errorf("sign jwt: %w", err)
	}
	return unsigned + "." + encodeSegment(mac.Sum(nil)), nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: encodeSegment(data []byte)
 * @Description //按 JWT 要求做不带填充的 base64url 编码
 * @Date :2026/10/23 10:39:00
 * @Param: data 待编码的原始字节
 * @return: base64url 字符串
 */
func encodeSegment(data []byte) string {
	return base64.RawURLEncoding.EncodeToString(data)
}
