/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //把 done 帧原样回写给 API
 * @File: client.go
 * @Time: 2026/10/23 10:39:00
 * @All Rights Reserve By Brtc
 */

// Package backend 把 done 帧异步 POST 到 API 的内部接口。
package backend

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"time"
)

const (
	postAttempts     = 3
	postInterval     = time.Second
	postTimeout      = 10 * time.Second
	maxResponseBytes = 1 << 20
)

// errSkipStore 表示接口返回成功但未落库（会话不存在或账号非法）。调用方记 warn，不重试。
var errSkipStore = errors.New("api skipped storing")

// statusError 是内部接口的 HTTP 或业务码失败。retryable 为 false 时不再重试。
type statusError struct {
	status    int
	code      string
	message   string
	retryable bool
}

// apiReply 是 POST /internal/messages 的响应体。
type apiReply struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Data    struct {
		Stored bool `json:"stored"`
	} `json:"data"`
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (e *statusError) Error()
 * @Description //拼出状态码、业务码和消息，供重试日志读取
 * @Date :2026/10/25 20:50:44
 * @Param: 无
 * @return: 错误文本
 */
func (e *statusError) Error() string {
	if e.code != "" {
		return fmt.Sprintf("internal message status %d code=%s message=%s", e.status, e.code, e.message)
	}
	return fmt.Sprintf("internal message status %d", e.status)
}

// Client 调用 API 内部消息接口。
type Client struct {
	endpoint string
	token    string
	http     *http.Client
	logger   *slog.Logger
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: New(apiBaseURL, token string, logger *slog.Logger)
 * @Description //创建回写客户端，目标为 API 的 /internal/messages
 * @Date :2026/10/23 10:39:00
 * @Param: apiBaseURL API 根地址；token 服务间令牌；logger 日志
 * @return: *Client
 */
func New(apiBaseURL, token string, logger *slog.Logger) *Client {
	return &Client{
		endpoint: apiBaseURL + "/internal/messages",
		token:    token,
		http:     &http.Client{Timeout: postTimeout},
		logger:   logger,
	}
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Client) DeliverAsync(frame []byte)
 * @Description //复制原始帧后在独立 goroutine 中回写，不阻塞调用方
 * @Date :2026/10/23 10:39:00
 * @Param: frame 网关下行的原始帧 JSON
 * @return: 无
 */
func (c *Client) DeliverAsync(frame []byte) {
	payload := make([]byte, len(frame))
	copy(payload, frame)
	go func() {
		if err := c.deliver(payload); err != nil {
			c.logger.Error("post internal message failed", slog.Any("err", err))
		}
	}()
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Client) deliver(payload []byte)
 * @Description //回写 done 帧。未落库只记 warn；4xx 不重试；其余失败最多 3 次，间隔 1 秒
 * @Date :2026/10/25 20:50:44
 * @Param: payload 原始帧 JSON
 * @return: 落库成功或明确跳过时返回 nil。不可重试的 4xx 或 3 次都失败时返回 error
 */
func (c *Client) deliver(payload []byte) error {
	var last error
	for attempt := 1; attempt <= postAttempts; attempt++ {
		last = c.post(payload)
		if last == nil {
			c.logger.Info("internal message posted", slog.Int("attempt", attempt))
			return nil
		}
		if errors.Is(last, errSkipStore) {
			c.logger.Warn("internal message skipped, conversation missing")
			return nil
		}
		var failed *statusError
		if errors.As(last, &failed) && !failed.retryable {
			c.logger.Error(
				"post internal message rejected",
				slog.Int("status", failed.status),
				slog.String("code", failed.code),
				slog.String("message", failed.message),
			)
			return last
		}
		if failed != nil {
			c.logger.Warn(
				"post internal message attempt failed",
				slog.Int("attempt", attempt),
				slog.String("code", failed.code),
				slog.String("message", failed.message),
				slog.Any("err", last),
			)
		} else {
			c.logger.Warn(
				"post internal message attempt failed",
				slog.Int("attempt", attempt),
				slog.Any("err", last),
			)
		}
		if attempt < postAttempts {
			time.Sleep(postInterval)
		}
	}
	return fmt.Errorf("post internal message after %d attempts: %w", postAttempts, last)
}

/**
 * @Author liaosiliang1234@126.com
 * @Function: (c *Client) post(payload []byte)
 * @Description //把原始帧 JSON 原样 POST 给 API，并按 HTTP 状态和业务码判定成败
 * @Date :2026/10/25 20:50:44
 * @Param: payload 原始帧 JSON
 * @return: 落库成功返回 nil。stored 为 false 返回 errSkipStore。4xx（不含 429）返回不可重试错误。5xx、429、业务码非 success、网络错误返回可重试错误
 */
func (c *Client) post(payload []byte) error {
	ctx, cancel := context.WithTimeout(context.Background(), postTimeout)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoint, bytes.NewReader(payload))
	if err != nil {
		return fmt.Errorf("build internal message request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Internal-Token", c.token)

	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("do internal message request: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(io.LimitReader(resp.Body, maxResponseBytes))
	if err != nil {
		return fmt.Errorf("read internal message response: %w", err)
	}

	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		parsed := apiReply{}
		_ = json.Unmarshal(raw, &parsed)
		retryable := resp.StatusCode == http.StatusTooManyRequests || resp.StatusCode >= http.StatusInternalServerError
		return &statusError{
			status:    resp.StatusCode,
			code:      parsed.Code,
			message:   parsed.Message,
			retryable: retryable,
		}
	}

	var parsed apiReply
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return fmt.Errorf("decode internal message response: %w", err)
	}
	if parsed.Code != "success" {
		return &statusError{
			status:    resp.StatusCode,
			code:      parsed.Code,
			message:   parsed.Message,
			retryable: true,
		}
	}
	if !parsed.Data.Stored {
		return errSkipStore
	}
	return nil
}
