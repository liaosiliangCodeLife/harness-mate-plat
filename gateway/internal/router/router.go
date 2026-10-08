// Package router 负责 ws_session_id 之间的点对点消息转发。
package router

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"

	gwlog "ws_gateway/internal/logging"
	"ws_gateway/internal/model"
	redisstore "ws_gateway/internal/redis"
	"ws_gateway/internal/ws"
)

// Router 聚合连接池与 Redis 映射，用于执行点对点转发。
type Router struct {
	Pool     *ws.SessionConnPool
	RedisMap *redisstore.Mapping
	Instance string
	Logger   *slog.Logger
}

// New 创建一个消息路由器。
func New(
	pool *ws.SessionConnPool,
	mapping *redisstore.Mapping,
	instance string,
	logger *slog.Logger,
) *Router {
	return &Router{
		Pool:     pool,
		RedisMap: mapping,
		Instance: instance,
		Logger:   logger,
	}
}

// RouteMessage 将消息按 to 字段转发到目标 ws_session_id。
func (r *Router) RouteMessage(conn *ws.SessionConn, rawMsg []byte) error {
	var inbound model.WSMessage
	if err := json.Unmarshal(rawMsg, &inbound); err != nil {
		return fmt.Errorf("unmarshal session message: %w", err)
	}
	if inbound.To == "" {
		return fmt.Errorf("to is required")
	}
	if inbound.To == conn.SessionID {
		r.Logger.Warn(
			"drop session message because target is self",
			slog.String("ws_session_id", conn.SessionID),
		)
		return nil
	}

	r.Logger.Debug(
		"session message received",
		slog.String("from", conn.SessionID),
		slog.String("to", inbound.To),
		slog.String("payload_preview", gwlog.PayloadPreview(rawMsg, 512)),
	)

	gateway, err := r.RedisMap.GetSessionGateway(context.Background(), inbound.To)
	if err != nil {
		return err
	}
	if gateway == "" {
		r.Logger.Warn(
			"drop session message because target is offline",
			slog.String("from", conn.SessionID),
			slog.String("to", inbound.To),
			slog.String("redis_key", fmt.Sprintf("ws:session:%s", inbound.To)),
		)
		return nil
	}
	if gateway != r.Instance {
		r.Logger.Warn(
			"drop session message because target is on another gateway",
			slog.String("from", conn.SessionID),
			slog.String("to", inbound.To),
			slog.String("target_gateway", gateway),
			slog.String("local_instance", r.Instance),
		)
		return nil
	}

	targetConn, ok := r.Pool.Get(inbound.To)
	if !ok {
		r.Logger.Warn(
			"drop session message because target connection not found locally",
			slog.String("from", conn.SessionID),
			slog.String("to", inbound.To),
		)
		return nil
	}

	outbound := model.WSMessage{
		To:   inbound.To,
		From: conn.SessionID,
		Data: inbound.Data,
	}
	payload, err := json.Marshal(outbound)
	if err != nil {
		return fmt.Errorf("marshal routed session message: %w", err)
	}
	if err := targetConn.Enqueue(payload); err != nil {
		r.Logger.Error(
			"route session message enqueue failed",
			slog.String("from", conn.SessionID),
			slog.String("to", inbound.To),
			slog.Any("err", err),
		)
		return err
	}
	r.Logger.Info(
		"route session message ok",
		slog.String("from", conn.SessionID),
		slog.String("to", inbound.To),
		slog.Int("bytes", len(payload)),
	)
	return nil
}
