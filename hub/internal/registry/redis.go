/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //把下行帧发布到账号 SSE 频道
 * @File: redis.go
 * @Time: 2026/10/24 17:50:49
 * @All Rights Reserve By Brtc
 */

// Package registry 把网关下行帧发布到账号 SSE 频道。
package registry

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"
	"time"

	redislib "github.com/redis/go-redis/v9"

	"hub/internal/model"
)

const (
	publishTimeout = 2 * time.Second
	pingTimeout    = 5 * time.Second
)

// Store 是 Hub 使用的 Redis 客户端。
type Store struct {
	client *redislib.Client
	logger *slog.Logger
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: New(ctx context.Context, redisURL string, logger *slog.Logger)
 * @Description //解析 Redis 地址、建立连接并执行一次 Ping
 * @Date :2026/10/23 10:39:00
 * @Param: ctx 用于 Ping 的上下文；redisURL Redis 连接串；logger 日志
 * @return: *Store；地址非法或 Ping 失败时返回 error
 */
func New(ctx context.Context, redisURL string, logger *slog.Logger) (*Store, error) {
	opts, err := redislib.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("parse redis url: %w", err)
	}

	client := redislib.NewClient(opts)
	pingCtx, cancel := context.WithTimeout(ctx, pingTimeout)
	defer cancel()
	if err := client.Ping(pingCtx).Err(); err != nil {
		_ = client.Close()
		return nil, fmt.Errorf("ping redis: %w", err)
	}

	logger.Info("redis connected", slog.String("addr", opts.Addr))
	return &Store{client: client, logger: logger}, nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (s *Store) Close()
 * @Description //关闭 Redis 连接
 * @Date :2026/10/23 10:39:00
 * @Param: 无
 * @return: 关闭失败时返回 error
 */
func (s *Store) Close() error {
	if err := s.client.Close(); err != nil {
		return fmt.Errorf("close redis: %w", err)
	}
	return nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (s *Store) Publish(accountID string, frame []byte)
 * @Description //把下行帧发布到账号 SSE 频道
 * @Date :2026/10/24 17:50:49
 * @Param: accountID 账号 ID；frame 原始帧 JSON
 * @return: account_id 为空或发布失败时返回 error
 */
func (s *Store) Publish(accountID string, frame []byte) error {
	accountID = strings.TrimSpace(accountID)
	if accountID == "" {
		return fmt.Errorf("account_id is required")
	}

	channel := fmt.Sprintf("stream:%s", accountID)
	ctx, cancel := context.WithTimeout(context.Background(), publishTimeout)
	defer cancel()

	if err := s.client.Publish(ctx, channel, frame).Err(); err != nil {
		return fmt.Errorf("redis publish %s: %w", channel, err)
	}

	s.logger.Debug(
		"redis frame published",
		slog.String("channel", channel),
		slog.Int("bytes", len(frame)),
	)
	return nil
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: RouteOf(frame model.WSMessage)
 * @Description //从两层 data 中取出 account_id、thread_id 和 done
 * @Date :2026/10/23 10:39:00
 * @Param: frame 网关下行帧，顶层 data 是业务信封
 * @return: accountID、threadID 为空表示取不到；done 仅在 data.data.done 为 JSON true 时为真
 */
func RouteOf(frame model.WSMessage) (accountID, threadID string, done bool) {
	// 先看内层 data.data（规格写明的位置），取不到再看业务信封。
	// Hermes 实际把 account_id / thread_id 放在信封上，done 放在 data.data。
	envelope := asObject(frame.Data)
	if envelope == nil {
		return "", "", false
	}
	inner := asObject(envelope["data"])
	accountID = firstNonEmpty(jsonString(inner["account_id"]), jsonString(envelope["account_id"]))
	threadID = firstNonEmpty(jsonString(inner["thread_id"]), jsonString(envelope["thread_id"]))
	done = jsonBool(inner["done"])
	return accountID, threadID, done
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: asObject(raw json.RawMessage)
 * @Description //把 JSON 对象或再包一层的 JSON 字符串解成对象
 * @Date :2026/10/23 10:39:00
 * @Param: raw 原始 JSON
 * @return: 字段到原始 JSON 的映射；不是对象时返回 nil
 */
func asObject(raw json.RawMessage) map[string]json.RawMessage {
	raw = bytes.TrimSpace(raw)
	if len(raw) == 0 || bytes.Equal(raw, []byte("null")) {
		return nil
	}
	if raw[0] == '"' {
		var encoded string
		if err := json.Unmarshal(raw, &encoded); err != nil {
			return nil
		}
		return asObject(json.RawMessage(encoded))
	}
	if raw[0] != '{' {
		return nil
	}
	var obj map[string]json.RawMessage
	if err := json.Unmarshal(raw, &obj); err != nil {
		return nil
	}
	return obj
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: jsonString(raw json.RawMessage)
 * @Description //把 JSON 字符串解出来并去掉首尾空白
 * @Date :2026/10/23 10:39:00
 * @Param: raw 字段原始 JSON
 * @return: 字符串；缺失、null 或非字符串时返回空串
 */
func jsonString(raw json.RawMessage) string {
	if len(bytes.TrimSpace(raw)) == 0 {
		return ""
	}
	var value string
	if err := json.Unmarshal(raw, &value); err != nil {
		return ""
	}
	return strings.TrimSpace(value)
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: jsonBool(raw json.RawMessage)
 * @Description //只把 JSON 布尔 true 认作真
 * @Date :2026/10/23 10:39:00
 * @Param: raw 字段原始 JSON
 * @return: 值为 true 时返回 true，其余情况返回 false
 */
func jsonBool(raw json.RawMessage) bool {
	if len(bytes.TrimSpace(raw)) == 0 {
		return false
	}
	var value bool
	if err := json.Unmarshal(raw, &value); err != nil {
		return false
	}
	return value
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: firstNonEmpty(values ...string)
 * @Description //返回第一个非空字符串
 * @Date :2026/10/23 10:39:00
 * @Param: values 候选字符串
 * @return: 第一个非空值；全都为空时返回空串
 */
func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if value != "" {
			return value
		}
	}
	return ""
}
