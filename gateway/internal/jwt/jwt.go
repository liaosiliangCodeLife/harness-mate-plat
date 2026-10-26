// Package jwt 提供 WebSocket 连接使用的 JWT 验签能力。
package jwt

import (
	"context"
	"fmt"
	"strings"

	jwtlib "github.com/golang-jwt/jwt/v5"

	"ws_gateway/internal/model"
)

// KeyProvider 按 bot_id 提供 HMAC 验签密钥。
type KeyProvider interface {
	KeyFor(ctx context.Context, botID string) (string, error)
}

// Verifier 先从 token 取出 bot_id，再取对应密钥做 HMAC 验签。
// provider 为空时才使用 fallbackSecret。
type Verifier struct {
	provider       KeyProvider
	fallbackSecret string
}

// NewVerifier 创建验签器。fallbackSecret 只在 provider 为 nil 时使用。
func NewVerifier(provider KeyProvider, fallbackSecret string) *Verifier {
	return &Verifier{provider: provider, fallbackSecret: fallbackSecret}
}

// ParseSessionToken 先不解签读取 ws_session_id，再按 bot 密钥验签。
// ws_session_id 为空时回退到 subject。任何一步失败都返回 error。
func (v *Verifier) ParseSessionToken(ctx context.Context, tokenStr string) (*model.SessionClaims, error) {
	if strings.TrimSpace(tokenStr) == "" {
		return nil, fmt.Errorf("token is required")
	}

	unverified := &model.SessionClaims{}
	if _, _, err := jwtlib.NewParser().ParseUnverified(tokenStr, unverified); err != nil {
		return nil, fmt.Errorf("parse token payload: %w", err)
	}

	botID := strings.TrimSpace(unverified.WSSessionID)
	if botID == "" {
		if sub, _ := unverified.GetSubject(); strings.TrimSpace(sub) != "" {
			botID = strings.TrimSpace(sub)
		} else {
			return nil, fmt.Errorf("token missing ws_session_id")
		}
	}

	key, err := v.resolveKey(ctx, botID)
	if err != nil {
		return nil, err
	}

	claims := &model.SessionClaims{}
	if err := parseSigned(tokenStr, claims, key); err != nil {
		return nil, err
	}
	if strings.TrimSpace(claims.WSSessionID) == "" {
		claims.WSSessionID = botID
	}
	return claims, nil
}

// resolveKey 向平台取密钥。未配置平台客户端时才使用共享回退密钥。
func (v *Verifier) resolveKey(ctx context.Context, botID string) (string, error) {
	if v.provider != nil {
		key, err := v.provider.KeyFor(ctx, botID)
		if err != nil {
			return "", fmt.Errorf("resolve bot key: %w", err)
		}
		if strings.TrimSpace(key) == "" {
			return "", fmt.Errorf("bot key is empty")
		}
		return key, nil
	}
	if strings.TrimSpace(v.fallbackSecret) == "" {
		return "", fmt.Errorf("jwt secret is not configured")
	}
	return v.fallbackSecret, nil
}

// parseSigned 用给定密钥做 HMAC-SHA256 验签。
func parseSigned(tokenStr string, claims *model.SessionClaims, key string) error {
	secret := []byte(key)
	token, err := jwtlib.ParseWithClaims(tokenStr, claims, func(token *jwtlib.Token) (any, error) {
		if _, ok := token.Method.(*jwtlib.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %s", token.Method.Alg())
		}
		return secret, nil
	})
	if err != nil {
		return fmt.Errorf("parse token: %w", err)
	}
	if !token.Valid {
		return fmt.Errorf("token is invalid")
	}
	return nil
}
