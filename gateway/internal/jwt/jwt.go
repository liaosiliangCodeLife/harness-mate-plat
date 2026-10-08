// Package jwt 提供 WebSocket 连接使用的 JWT 验签能力。
package jwt

import (
	"fmt"
	"strings"

	jwtlib "github.com/golang-jwt/jwt/v5"

	"ws_gateway/internal/model"
)

// Verifier 负责使用共享密钥解析并校验 JWT。
type Verifier struct {
	secret []byte
}

// NewVerifier 创建一个基于 HMAC 密钥的 JWT 验签器。
func NewVerifier(secret string) *Verifier {
	return &Verifier{secret: []byte(secret)}
}

// ParseSessionToken 解析连接 JWT，并确保 ws_session_id 合法。
// ws_session_id 为空时 fallback 到 subject 字段。
func (v *Verifier) ParseSessionToken(tokenStr string) (*model.SessionClaims, error) {
	claims := &model.SessionClaims{}
	if err := v.parse(tokenStr, claims); err != nil {
		return nil, err
	}
	if strings.TrimSpace(claims.WSSessionID) == "" {
		if sub, _ := claims.GetSubject(); strings.TrimSpace(sub) != "" {
			claims.WSSessionID = sub
		} else {
			return nil, fmt.Errorf("token missing ws_session_id")
		}
	}
	return claims, nil
}

func (v *Verifier) parse(tokenStr string, claims jwtlib.Claims) error {
	if strings.TrimSpace(tokenStr) == "" {
		return fmt.Errorf("token is required")
	}

	token, err := jwtlib.ParseWithClaims(tokenStr, claims, func(token *jwtlib.Token) (any, error) {
		if _, ok := token.Method.(*jwtlib.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %s", token.Method.Alg())
		}
		return v.secret, nil
	})
	if err != nil {
		return fmt.Errorf("parse token: %w", err)
	}
	if !token.Valid {
		return fmt.Errorf("token is invalid")
	}
	return nil
}
