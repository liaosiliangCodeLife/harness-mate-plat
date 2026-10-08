package redis

import (
	"context"
	"fmt"
	"log/slog"
	"strings"

	redislib "github.com/redis/go-redis/v9"
)

// SessionConnectionManager 定义按 ws_session_id 关闭本地连接所需的最小能力。
type SessionConnectionManager interface {
	// CloseSession 关闭指定会话连接；若会话不在本机可直接返回 nil。
	CloseSession(ctx context.Context, sessionID string) error
}

// Subscriber 负责监听 kick_session:* Redis Pub/Sub 频道。
type Subscriber struct {
	client  *redislib.Client
	manager SessionConnectionManager
	logger  *slog.Logger
}

// NewSubscriber 创建一个 Redis Pub/Sub 订阅器。
func NewSubscriber(
	client *redislib.Client,
	manager SessionConnectionManager,
	logger *slog.Logger,
) *Subscriber {
	return &Subscriber{
		client:  client,
		manager: manager,
		logger:  logger,
	}
}

// Subscribe 持续监听 kick_session:* 频道，直到 ctx 结束。
func (s *Subscriber) Subscribe(ctx context.Context) error {
	pubsub := s.client.PSubscribe(ctx, "kick_session:*")
	defer func() {
		if err := pubsub.Close(); err != nil {
			s.logger.Error("close pubsub failed", slog.Any("err", err))
		}
	}()

	if _, err := pubsub.Receive(ctx); err != nil {
		return fmt.Errorf("subscribe pubsub: %w", err)
	}

	channel := pubsub.Channel()
	for {
		select {
		case <-ctx.Done():
			return nil
		case msg, ok := <-channel:
			if !ok {
				return nil
			}
			if err := s.handleMessage(ctx, msg); err != nil {
				s.logger.Error("handle pubsub message failed", slog.String("channel", msg.Channel), slog.Any("err", err))
			}
		}
	}
}

func (s *Subscriber) handleMessage(ctx context.Context, msg *redislib.Message) error {
	if !strings.HasPrefix(msg.Channel, "kick_session:") {
		s.logger.Warn("ignored unknown pubsub channel", slog.String("channel", msg.Channel))
		return nil
	}
	sessionID := strings.TrimPrefix(msg.Channel, "kick_session:")
	if sessionID == "" {
		return fmt.Errorf("empty ws_session_id in channel %s", msg.Channel)
	}
	s.logger.Info("received kick session", slog.String("ws_session_id", sessionID))
	return s.manager.CloseSession(ctx, sessionID)
}
