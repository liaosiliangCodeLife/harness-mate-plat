// Package platform 按 bot_id 向平台 API 获取验签密钥，并做短时缓存。
package platform

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

const (
	keyTimeout       = 3 * time.Second
	maxResponseBytes = 1 << 20
)

// entry 是一条未过期前可复用的 bot 密钥。
type entry struct {
	key       string
	expiresAt time.Time
}

// Client 调用平台内部接口读取 bot 验签密钥。
type Client struct {
	baseURL string
	token   string
	ttl     time.Duration
	logger  *slog.Logger
	http    *http.Client
	mu      sync.RWMutex
	cache   map[string]entry
}

// New 创建平台客户端。baseURL 是平台 API 根地址，token 放在 X-Internal-Token。
func New(baseURL, token string, ttl time.Duration, logger *slog.Logger) *Client {
	return &Client{
		baseURL: strings.TrimRight(strings.TrimSpace(baseURL), "/"),
		token:   token,
		ttl:     ttl,
		logger:  logger,
		http:    &http.Client{Timeout: keyTimeout},
		cache:   map[string]entry{},
	}
}

// KeyFor 返回 bot 的验签密钥。命中未过期缓存则直接返回；失败结果不写入缓存。
func (c *Client) KeyFor(ctx context.Context, botID string) (string, error) {
	botID = strings.TrimSpace(botID)
	if botID == "" {
		return "", fmt.Errorf("bot_id is required")
	}
	if key, ok := c.cached(botID); ok {
		return key, nil
	}

	key, err := c.fetch(ctx, botID)
	if err != nil {
		return "", err
	}
	c.store(botID, key)
	return key, nil
}

// cached 读取未过期的密钥。过期项留到下次写入时清理。
func (c *Client) cached(botID string) (string, bool) {
	c.mu.RLock()
	item, ok := c.cache[botID]
	c.mu.RUnlock()
	if !ok || !item.expiresAt.After(time.Now()) {
		return "", false
	}
	return item.key, true
}

// store 写入缓存，并清掉已经过期的项。日志不记录密钥本身。
func (c *Client) store(botID, key string) {
	now := time.Now()
	c.mu.Lock()
	defer c.mu.Unlock()
	for id, item := range c.cache {
		if !item.expiresAt.After(now) {
			delete(c.cache, id)
		}
	}
	c.cache[botID] = entry{key: key, expiresAt: now.Add(c.ttl)}
}

// fetch 向平台查询密钥。4xx、5xx 和网络错误都返回 error，调用方不得放行。
func (c *Client) fetch(ctx context.Context, botID string) (string, error) {
	reqCtx, cancel := context.WithTimeout(ctx, keyTimeout)
	defer cancel()

	endpoint := c.baseURL + "/internal/bot-key?bot_id=" + url.QueryEscape(botID)
	req, err := http.NewRequestWithContext(reqCtx, http.MethodGet, endpoint, nil)
	if err != nil {
		return "", fmt.Errorf("build bot key request: %w", err)
	}
	req.Header.Set("X-Internal-Token", c.token)

	resp, err := c.http.Do(req)
	if err != nil {
		c.logger.Warn("fetch bot key failed", slog.String("bot_id", botID), slog.Any("err", err))
		return "", fmt.Errorf("do bot key request: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(io.LimitReader(resp.Body, maxResponseBytes))
	if err != nil {
		return "", fmt.Errorf("read bot key response: %w", err)
	}
	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		c.logger.Warn(
			"fetch bot key rejected",
			slog.String("bot_id", botID),
			slog.Int("status", resp.StatusCode),
		)
		return "", fmt.Errorf("bot key status %d", resp.StatusCode)
	}

	var parsed struct {
		Code string `json:"code"`
		Data struct {
			Key string `json:"key"`
		} `json:"data"`
	}
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return "", fmt.Errorf("decode bot key response: %w", err)
	}
	if parsed.Code != "success" || strings.TrimSpace(parsed.Data.Key) == "" {
		c.logger.Warn(
			"fetch bot key rejected",
			slog.String("bot_id", botID),
			slog.String("code", parsed.Code),
		)
		return "", fmt.Errorf("bot key rejected: %s", parsed.Code)
	}
	return parsed.Data.Key, nil
}
