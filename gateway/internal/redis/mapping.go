package redis

import (
	"context"
	"fmt"
	"log/slog"

	redislib "github.com/redis/go-redis/v9"
)

// Mapping 封装 ws:session:* Redis 映射操作。
type Mapping struct {
	client *redislib.Client
	logger *slog.Logger
}

// NewMapping 创建一个 Redis 映射操作对象。
func NewMapping(client *redislib.Client, logger *slog.Logger) *Mapping {
	return &Mapping{client: client, logger: logger}
}

// SessionOnline 记录 ws_session_id 所在网关实例。
func (m *Mapping) SessionOnline(ctx context.Context, sessionID, instance string) error {
	if err := m.client.Set(ctx, sessionKey(sessionID), instance, 0).Err(); err != nil {
		return fmt.Errorf("session online: %w", err)
	}
	m.logger.Debug(
		"session online stored",
		slog.String("ws_session_id", sessionID),
		slog.String("instance", instance),
	)
	return nil
}

// SessionOffline 删除 ws_session_id 网关映射。
func (m *Mapping) SessionOffline(ctx context.Context, sessionID string) error {
	if err := m.client.Del(ctx, sessionKey(sessionID)).Err(); err != nil {
		return fmt.Errorf("session offline: %w", err)
	}
	m.logger.Debug("session offline removed", slog.String("ws_session_id", sessionID))
	return nil
}

// GetSessionGateway 查询 ws_session_id 所在网关实例。
func (m *Mapping) GetSessionGateway(ctx context.Context, sessionID string) (string, error) {
	value, err := m.client.Get(ctx, sessionKey(sessionID)).Result()
	if err != nil {
		if err == redislib.Nil {
			return "", nil
		}
		return "", fmt.Errorf("get session gateway: %w", err)
	}
	return value, nil
}

func sessionKey(sessionID string) string {
	return fmt.Sprintf("ws:session:%s", sessionID)
}
