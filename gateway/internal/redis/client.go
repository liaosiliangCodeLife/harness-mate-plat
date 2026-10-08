// Package redis 封装网关对 Redis 的连接、映射与 Pub/Sub 操作。
package redis

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	redislib "github.com/redis/go-redis/v9"
)

// NewClient 根据 Redis URL 初始化客户端并执行一次连通性检测。
func NewClient(ctx context.Context, redisURL string, logger *slog.Logger) (*redislib.Client, error) {
	opts, err := redislib.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("parse redis url: %w", err)
	}

	client := redislib.NewClient(opts)

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	if err := client.Ping(pingCtx).Err(); err != nil {
		_ = client.Close()
		return nil, fmt.Errorf("ping redis: %w", err)
	}

	logger.Info("redis connected", slog.String("addr", opts.Addr))
	return client, nil
}
